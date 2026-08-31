import { expect, test } from "@playwright/test";
import { unlink, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

test.describe("workspace shell", () => {
  test("loads the workspace navigation", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("TMS", { exact: true })).toBeVisible();
    const menu = page.getByRole("button", { name: "Open workspace menu" });
    await expect(menu).toBeVisible();
    await menu.click();
    const sections = page.getByRole("navigation", { name: "Workspace sections" });
    await expect(sections).toBeVisible();
    await expect(sections.getByRole("button", { name: "Directory" })).toBeVisible();
    await expect(sections.getByRole("button", { name: "Runs" })).toBeVisible();
    await expect(sections.getByRole("button", { name: "Reports" })).toBeVisible();
    await expect(sections.getByRole("button", { name: "Enums" })).toBeVisible();
    await expect(page.getByRole("button", { name: "New project" })).toBeVisible();
  });

  test("expands and collapses directory folders without losing state on refresh", async ({ page, request }) => {
    const project = `pw_tree_${Date.now()}`;
    const module = "Checkout";
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: module } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: `${project}/${module}`, file_name: "case", scenario_name: "Case", description: "Initial" } })).status()).toBe(201);
      await page.goto("/");
      const sidebar = page.locator("aside.sidebar");
      const projectFolder = sidebar.locator("button.tree-item").filter({ hasText: project }).first();
      await expect(projectFolder).toHaveAttribute("aria-expanded", "false");
      await expect(sidebar.locator(".tree-toggle")).toHaveCount(0);
      await expect(sidebar.locator("button.tree-item").filter({ hasText: module })).toHaveCount(0);
      await projectFolder.click();
      await expect(projectFolder).toHaveAttribute("aria-expanded", "true");
      const moduleFolder = sidebar.locator("button.tree-item").filter({ hasText: module }).first();
      await expect(moduleFolder).toHaveAttribute("aria-expanded", "false");
      await moduleFolder.click();
      await expect(sidebar.locator("button.tree-item").filter({ hasText: "case.feature" })).toBeVisible();
      await sidebar.getByRole("button", { name: "Refresh" }).click();
      await expect(sidebar.locator("button.tree-item").filter({ hasText: "case.feature" })).toBeVisible();
      await projectFolder.click();
      await expect(sidebar.locator("button.tree-item").filter({ hasText: module })).toHaveCount(0);
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("opens child folders from directory details", async ({ page, request }) => {
    const project = `pw_folder_links_${Date.now()}`;
    const module = "Checkout";
    const nested = "Regression";
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: module } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: `${project}/${module}`, name: nested } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: `${project}/${module}/${nested}`, file_name: "case", scenario_name: "Case", description: "Initial" } })).status()).toBe(201);
      await page.goto("/");
      const details = page.locator("section.content");
      await details.getByRole("button", { name: project, exact: true }).click();
      await expect(details.locator(".card-header strong").filter({ hasText: project })).toBeVisible();
      await details.getByRole("button", { name: module, exact: true }).click();
      await expect(details.locator(".card-header strong").filter({ hasText: `${project}/${module}` })).toBeVisible();
      await expect(details.getByRole("button", { name: "+ Sub-folder", exact: true })).toBeVisible();
      await expect(details.getByRole("button", { name: "+ Scenario", exact: true })).toBeVisible();
      await expect(details.getByRole("button", { name: "Back to parent folder" })).toBeVisible();
      await details.getByRole("button", { name: nested, exact: true }).click();
      await expect(details.locator(".card-header strong").filter({ hasText: `${project}/${module}/${nested}` })).toBeVisible();
      await expect(details.getByRole("button", { name: "Rename folder" })).toBeVisible();
      await expect(details.getByRole("button", { name: "Delete folder" })).toBeVisible();
      await details.locator("tbody tr").filter({ hasText: "Case" }).click();
      await expect(details.getByText(`${project}/${module}/${nested}/case.feature`, { exact: true })).toBeVisible();
      await details.getByRole("button", { name: "Back to parent folder" }).click();
      await expect(details.locator(".card-header strong").filter({ hasText: `${project}/${module}/${nested}` })).toBeVisible();
      await details.getByRole("button", { name: "Back to parent folder" }).click();
      await expect(details.locator(".card-header strong").filter({ hasText: `${project}/${module}` })).toBeVisible();
      await details.getByRole("button", { name: "Back to parent folder" }).click();
      await expect(details.locator(".card-header strong").filter({ hasText: project })).toBeVisible();
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("compacts directory metadata and opens scenario details from table rows", async ({ page }) => {
    await page.goto("/?tab=directory&project=test-proj01&path=test-proj01%2FmoduleA");
    const row = page.locator("tbody tr").filter({ hasText: "scenario name but different" });
    await expect(row).toBeVisible();
    await expect(row.locator("td")).toHaveCount(4);
    await expect(row.locator("td").nth(1).locator(".tag")).toHaveCount(2);
    await expect(row.locator("td").nth(1).locator(".inline-more")).toHaveText("...");
    await expect(row.locator("td").nth(2).locator(".tag")).toHaveCount(1);
    await expect(row.locator("td").nth(2).locator(".inline-more")).toHaveText("...");
    await expect(row.getByText("test_case1.feature", { exact: true })).toHaveCount(0);
    await expect(row.getByRole("button", { name: "Edit test_case1.feature" })).toBeVisible();
    await expect(row.getByRole("button", { name: "Remove test_case1.feature" })).toBeVisible();
    await row.click();
    await expect(page.getByText("test-proj01/moduleA/test_case1.feature", { exact: true })).toBeVisible();
  });

  test("paginates directory scenarios with selectable page sizes", async ({ page, request }) => {
    const project = `pw_pages_${Date.now()}`;
    const parent = `${project}/Checkout`;
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Checkout" } })).status()).toBe(201);
      for (let index = 1; index <= 21; index += 1) {
        expect((await request.post("/api/files", { data: { parent, file_name: `case-${index}`, scenario_name: `Scenario ${index}`, description: "Initial" } })).status()).toBe(201);
      }
      await page.goto(`/?tab=directory&project=${encodeURIComponent(project)}&path=${encodeURIComponent(parent)}`);
      const rows = page.locator("tbody tr");
      const pageSize = page.getByLabel("Scenarios per page");
      await expect(rows).toHaveCount(20);
      await expect(pageSize).toHaveValue("20");
      await expect(page.locator(".table-pagination")).toContainText("1 - 20 of 21");
      await expect(pageSize.locator("option")).toHaveText(["20", "50", "100"]);
      await page.getByRole("button", { name: "Next", exact: true }).click();
      await expect(rows).toHaveCount(1);
      await expect(page.locator(".table-pagination")).toContainText("21 - 21 of 21");
      await pageSize.selectOption("50");
      await expect(rows).toHaveCount(21);
      await expect(page.locator(".table-pagination")).toContainText("1 - 21 of 21");
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("keeps the navigation visible at a narrow viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await page.getByRole("button", { name: "Open workspace menu" }).click();
    await expect(page.getByRole("navigation", { name: "Workspace sections" })).toBeVisible();
  });

  test("rehydrates the selected workspace tab from a direct URL", async ({ page }) => {
    await page.goto("/?tab=reports&project=Alpha");
    await page.getByRole("button", { name: "Open workspace menu" }).click();
    const sections = page.getByRole("navigation", { name: "Workspace sections" });
    await expect(sections.getByRole("button", { name: "Reports" })).toHaveClass(/active/);
    await expect(page.locator("header").getByText("Alpha", { exact: true })).toBeVisible();
    await sections.getByRole("button", { name: "Directory" }).click();
    await expect(page).toHaveURL(/\/\?tab=directory/);
  });

  test("loads a legacy /ui file link through the Next shell", async ({ page }) => {
    await page.goto("/ui/file/test-proj01/moduleA/t1.feature");
    await expect(page.getByText("test-proj01/moduleA/t1.feature", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Structured" })).toBeVisible();
  });

  test("uses placeholders instead of structured-editor field labels", async ({ page }) => {
    await page.goto("/ui/file/test-proj01/moduleA/t1.feature");
    const editor = page.locator(".structured-editor");
    await expect(editor.getByPlaceholder("Description")).toBeVisible();
    await expect(editor.getByLabel("Feature description")).toHaveAttribute("rows", "2");
    await expect(editor.getByPlaceholder("Add feature tag")).toBeVisible();
    await expect(editor.getByPlaceholder("Scenario name")).toBeVisible();
    await expect(editor.getByPlaceholder("Add scenario tag")).toBeVisible();
    await expect(editor.getByText("Feature description", { exact: true })).toHaveCount(0);
    await expect(editor.getByText("Feature tags (comma-separated)", { exact: true })).toHaveCount(0);
    await expect(editor.getByText("Scenario name", { exact: true })).toHaveCount(0);
    await expect(editor.getByText("Scenario tags (comma-separated)", { exact: true })).toHaveCount(0);
  });

  test("adds only entered tag to an empty tag list", async ({ page, request }) => {
    const project = `pw_tag_${Date.now()}`;
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Checkout" } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: `${project}/Checkout`, file_name: "case", scenario_name: "Case", description: "Initial" } })).status()).toBe(201);
      await page.goto(`/ui/file/${project}/Checkout/case.feature`);
      const featureTags = page.locator(".structured-editor").getByLabel("Feature tags");
      await featureTags.fill("new-tag");
      await featureTags.dispatchEvent("compositionstart");
      await featureTags.dispatchEvent("keydown", { key: "Enter", isComposing: true });
      await expect(page.locator(".tag-editor").first().locator(".tag-chip")).toHaveCount(0);
      await expect(featureTags).toHaveValue("new-tag");
      await featureTags.dispatchEvent("compositionend");
      await featureTags.press("Enter");
      await expect(page.locator(".tag-editor").first().locator(".tag-chip")).toHaveText(["@new-tag"]);
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("uses icon controls for step removal and optional data tables", async ({ page }) => {
    await page.goto("/ui/file/test-proj01/moduleA/t1.feature");
    const editor = page.locator(".structured-editor");
    await expect(editor.getByRole("button", { name: "Remove step 1" })).toBeVisible();
    const addDataTable = editor.getByRole("button", { name: "Add data table, 1 row per line, split by |" }).first();
    await expect(addDataTable).toHaveAttribute("title", "Add data table, 1 row per line, split by |");
    await addDataTable.click();
    await expect(editor.getByLabel("Step 1 data table")).toBeVisible();
  });

  test("adds and removes feature, scenario, and example tags as @ chips", async ({ page }) => {
    await page.goto("/ui/file/test-proj01/moduleA/t1.feature");
    const editor = page.locator(".structured-editor");
    await expect(editor.getByText("@feature-tag1", { exact: true })).toBeVisible();
    const featureTags = editor.getByLabel("Feature tags");
    await featureTags.fill("@new-feature");
    await featureTags.press("Enter");
    await expect(editor.getByText("@new-feature", { exact: true })).toBeVisible();
    await expect(featureTags).toHaveValue("");
    await editor.getByRole("button", { name: "Remove tag @new-feature" }).click();
    await expect(editor.getByText("@new-feature", { exact: true })).toHaveCount(0);

    const scenarioTags = editor.getByLabel("Scenario tags");
    await scenarioTags.fill("new-scenario");
    await scenarioTags.press("Enter");
    await expect(editor.getByText("@new-scenario", { exact: true })).toBeVisible();

    await editor.getByRole("button", { name: "Scenario", exact: true }).click();
    await editor.getByRole("button", { name: "Add examples", exact: true }).click();
    const exampleTags = editor.getByLabel("Example 1 tags");
    await exampleTags.fill("example-tag");
    await exampleTags.press("Enter");
    await expect(editor.getByText("@example-tag", { exact: true })).toBeVisible();
    await editor.getByRole("button", { name: "Remove tag @example-tag" }).click();
    await expect(editor.getByText("@example-tag", { exact: true })).toHaveCount(0);
  });

  test("uses compact scenario controls and autosized data tables", async ({ page }) => {
    await page.goto("/ui/file/test-proj01/moduleA/t1.feature");
    const editor = page.locator(".structured-editor");
    const scenario = editor.locator(".editor-section").nth(1);
    await expect(editor.getByLabel("Scenario kind")).toHaveCount(0);
    const scenarioType = scenario.getByRole("button", { name: "Scenario", exact: true });
    await expect(scenarioType).toBeVisible();
    await scenarioType.click();
    await expect(scenario.getByRole("button", { name: "Scenario Outline", exact: true })).toBeVisible();
    const steps = scenario.locator(".step-editor");
    const before = await steps.count();
    await scenario.getByRole("button", { name: "New step", exact: true }).click();
    await expect(steps).toHaveCount(before + 1);
    const addDataTable = scenario.getByRole("button", { name: "Add data table, 1 row per line, split by |" }).first();
    await expect(addDataTable.evaluate((element) => element.parentElement?.classList.contains("step-fields"))).resolves.toBe(true);
    const dataTable = editor.getByLabel("Step 2 data table");
    await expect(dataTable).toBeVisible();
    await expect(dataTable.evaluate((element) => element.clientHeight + 1 >= element.scrollHeight)).resolves.toBe(true);
  });

  test("rehydrates and executes a bookmarked search", async ({ page }) => {
    await page.goto("/?q=scenario%20name&scope=project%3Atest-proj01");
    await expect(page.getByText("test-proj01/moduleC/test case 3.feature", { exact: true })).toBeVisible();
    await expect(page.getByText("Search results", { exact: true })).toBeVisible();
  });

  test("opens legacy run and report links in their target tabs", async ({ page }) => {
    await page.goto("/ui/run/test-proj01/test-run/tr1.yaml");
    await page.getByRole("button", { name: "Open workspace menu" }).click();
    await expect(page.getByRole("navigation", { name: "Workspace sections" }).getByRole("button", { name: "Runs" })).toHaveClass(/active/);
    await expect(page.getByRole("button", { name: "tr1", exact: true })).toBeVisible();
    await page.goto("/ui/report/test-proj01/report-01.yaml");
    await page.getByRole("button", { name: "Open workspace menu" }).click();
    await expect(page.getByRole("navigation", { name: "Workspace sections" }).getByRole("button", { name: "Reports" })).toHaveClass(/active/);
    await expect(page.getByRole("button", { name: "report 01", exact: true })).toBeVisible();
  });

  test("protects a dirty feature editor from tab switching", async ({ page }) => {
    await page.goto("/ui/file/test-proj01/moduleA/t1.feature");
    await page.getByRole("button", { name: "Raw" }).click();
    const editor = page.locator("textarea.editor");
    await editor.fill(`${await editor.inputValue()}\n# browser draft`);
    await expect(page.getByText("Unsaved", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Open workspace menu" }).click();
    await page.getByRole("navigation", { name: "Workspace sections" }).getByRole("button", { name: "Runs" }).click();
    const confirmation = page.getByRole("dialog");
    await expect(confirmation).toContainText("Discard unsaved feature changes");
    await confirmation.getByRole("button", { name: "Cancel" }).click();
    await page.getByRole("button", { name: "Open workspace menu" }).click();
    await expect(page.getByRole("navigation", { name: "Workspace sections" }).getByRole("button", { name: "Directory" })).toHaveClass(/active/);
  });

  test("creates a project, imports multiple features, and deletes the folder", async ({ page, request }) => {
    const project = `pw_browser_${Date.now()}`;
    const module = "imported";
    try {
      const created = await request.post("/api/folders", { data: { parent: "", name: project } });
      expect(created.status()).toBe(201);
      await page.goto("/");
      const projectButton = page.locator("button.tree-item").filter({ hasText: project }).first();
      await expect(projectButton).toBeVisible();
      await projectButton.click();
      await page.getByRole("button", { name: "New module" }).click();
      const createModule = page.getByRole("dialog");
      await createModule.getByLabel("Name").fill(module);
      await createModule.getByRole("button", { name: "Create" }).click();
      const moduleButton = page.locator("button.tree-item").filter({ hasText: module }).last();
      await expect(moduleButton).toBeVisible();
      await moduleButton.click();
      await page.getByRole("button", { name: "Import files", exact: true }).click();
      await expect(page.getByText("Drop `.feature` files here", { exact: true })).toBeVisible();
      const importDialog = page.locator(".import-dialog");
      await expect(importDialog.getByRole("button", { name: "Import files", exact: true })).toBeDisabled();
      await page.locator(".dropzone").evaluate((element) => {
        const transfer = new DataTransfer();
        transfer.items.add(new File(["Feature: First\n\nScenario: Alpha scenario\n  Given a step\n"], "first.feature", { type: "text/plain" }));
        transfer.items.add(new File(["Feature: Second\n\nScenario: Beta scenario\n  Given another step\n"], "second.feature", { type: "text/plain" }));
        element.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: transfer }));
      });
      await importDialog.getByRole("button", { name: "Import 2 files", exact: true }).click();
      await expect(page.locator("tbody tr").filter({ hasText: "Alpha scenario" })).toBeVisible();
      await expect(page.locator("tbody tr").filter({ hasText: "Beta scenario" })).toBeVisible();
      await page.getByPlaceholder("Filter scenario name…").fill("Beta scenario");
      await expect(page.locator("tbody tr").filter({ hasText: "Alpha scenario" })).toHaveCount(0);
      await expect(page.locator("tbody tr").filter({ hasText: "Beta scenario" })).toBeVisible();
      await page.getByPlaceholder("Filter scenario name…").fill("");
      await page.getByRole("button", { name: "Delete folder" }).click();
      const deleteFolder = page.getByRole("dialog");
      await expect(deleteFolder).toContainText(`Delete ${project}/${module} and its contents?`);
      await deleteFolder.getByRole("button", { name: "Delete" }).click();
      await expect(page.locator("button.tree-item").filter({ hasText: module })).toHaveCount(0);
      const deleted = await request.get(`/api/folders/${project}/${module}/contents`);
      expect(deleted.status()).toBe(404);
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("edits a run and creates a report through the workspace panels", async ({ page, request }) => {
    const project = `pw_panels_${Date.now()}`;
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Checkout" } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: `${project}/Checkout`, file_name: "case", scenario_name: "Case", description: "Case" } })).status()).toBe(201);
      expect((await request.post(`/api/runs/${project}/groups`, { data: { name: "smoke" } })).status()).toBe(201);
      expect((await request.post("/api/runs", { data: { project, group: "smoke", file_name: "run", name: "Browser run", case_paths: [] } })).status()).toBe(201);
      await page.goto(`/?tab=runs&project=${encodeURIComponent(project)}`);
      await page.getByRole("button", { name: "Browser run", exact: true }).click();
      await page.locator("textarea").first().fill("edited in browser");
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await expect(page.getByText("Saved", { exact: true })).toBeVisible();
      await page.getByRole("button", { name: "Reports", exact: true }).click();
      await page.getByRole("button", { name: "New report", exact: true }).click();
      await page.getByLabel("Title").fill("Browser inventory");
      await page.locator("form.report-form select").first().selectOption("tag_inventory");
      await expect(page.locator("form.report-form select").first()).toHaveValue("tag_inventory");
      await page.locator('form.report-form input[placeholder="release"]').fill("smoke");
      await page.getByRole("button", { name: "Create report", exact: true }).click();
      await expect(page.getByText("Browser inventory", { exact: true })).toBeVisible();
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("previews and imports an Allure report into a run", async ({ page, request }) => {
    const project = `pw_allure_${Date.now()}`;
    const scenarioPath = `${project}/Checkout/case.feature`;
    const suites = { name: "root", children: [{ name: "Buy", status: "passed", time: { start: 1700000000000, stop: 1700000001000 } }] };
    const summary = { reportName: "Nightly", time: { start: 1700000000000 } };
    const encoded = (value: unknown) => Buffer.from(JSON.stringify(value), "utf8").toString("base64");
    const html = `<html><body><script>d('data/suites.json','${encoded(suites)}');d('widgets/summary.json','${encoded(summary)}');</script></body></html>`;
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Checkout" } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: `${project}/Checkout`, file_name: "case", scenario_name: "Buy", description: "Purchase" } })).status()).toBe(201);
      expect((await request.post(`/api/runs/${project}/groups`, { data: { name: "smoke" } })).status()).toBe(201);
      await page.goto(`/?tab=runs&project=${encodeURIComponent(project)}`);
      await page.getByRole("button", { name: "Import Allure", exact: true }).click();
      await page.locator(".run-import-form select").first().selectOption({ label: `${project} / smoke` });
      await page.locator('input[type="file"][accept=".html,.htm,text/html"]').setInputFiles({ name: "report.html", mimeType: "text/html", buffer: Buffer.from(html) });
      await expect(page.getByText(/Nightly ·/)).toBeVisible();
      await page.getByPlaceholder("allure-import.yaml").fill("nightly");
      await page.getByPlaceholder("Imported run").fill("Imported Nightly");
      await page.getByRole("button", { name: "Import run", exact: true }).click();
      await expect(page.getByRole("button", { name: "Imported Nightly", exact: true })).toBeVisible();
      const imported = await request.get(`/api/runs/${project}/smoke/nightly.yaml`);
      expect(imported.status()).toBe(200);
      await expect(imported.json()).resolves.toMatchObject({ name: "Imported Nightly", created_at: "2023-11-14T22:13:20+00:00", results: [{ file_path: scenarioPath, result: "PASSED" }] });
      await page.locator(".run-table tbody tr").filter({ hasText: "Imported Nightly" }).click();
      const result = page.locator("select.case-status");
      await expect(result).toHaveValue("PASSED");
      await expect(result).toHaveClass(/status-passed/);
      await expect(page.getByText("Buy", { exact: true })).toBeVisible();
      await expect(page.getByText(scenarioPath, { exact: true })).toHaveCount(0);
      const remark = page.getByRole("button", { name: "Add remark for Buy" });
      await remark.click();
      await expect(page.getByPlaceholder("Remark")).toHaveAttribute("rows", "2");
      await expect(page.getByRole("button", { name: `Remove ${scenarioPath}` })).toBeVisible();
      for (const [status, color] of [["FAILED", "rgb(185, 28, 28)"], ["EXECUTING", "rgb(3, 105, 161)"], ["SKIPPED", "rgb(126, 34, 206)"], ["PENDING", "rgb(194, 65, 12)"]] as const) {
        await result.selectOption(status);
        await expect(result).toHaveClass(new RegExp(`status-${status.toLowerCase()}`));
        await expect(result).toHaveCSS("color", color);
      }
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("opens a report computed view and saves its folder scope", async ({ page, request }) => {
    const project = `pw_report_view_${Date.now()}`;
    const reportPath = `${project}/report/inventory.yaml`;
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Checkout" } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: `${project}/Checkout`, file_name: "case", scenario_name: "Case", description: "Purchase" } })).status()).toBe(201);
      expect((await request.post(`/api/reports/${project}`, { data: { file_name: "inventory.yaml", title: "Inventory", type: "tag_inventory", created_at: "2024-01-01T00:00:00+00:00", tag: "release", scope: `${project}/Checkout` } })).status()).toBe(201);
      await page.goto(`/?tab=reports&project=${encodeURIComponent(project)}`);
      await page.locator("tbody tr").filter({ hasText: "Inventory" }).click();
      await expect(page.locator(".card-header strong").filter({ hasText: /^Inventory tag_inventory$/ })).toBeVisible();
      await expect(page.getByText("Result view", { exact: true })).toBeVisible();
      await expect(page.getByText("not carrying", { exact: true })).toBeVisible();
      await expect(page.locator(".report-buckets details").first()).toHaveAttribute("open", "");
      await expect(page.locator(".report-case-groups li")).toHaveText("Case");
      await expect(page.getByText(`${project}/Checkout/case.feature`, { exact: true })).toHaveCount(0);
      const scope = page.locator("section.report-source-editor input");
      await scope.fill(project);
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await expect(page.getByText("Saved", { exact: true })).toBeVisible();
      await expect(scope).toHaveValue(project);
      const saved = await request.get(`/api/reports/${project}/inventory.yaml`);
      expect(saved.status()).toBe(200);
      await expect(saved.json()).resolves.toMatchObject({ scope: project, tag: "release" });
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("opens a report source run from its clickable row", async ({ page, request }) => {
    const project = `pw_report_run_${Date.now()}`;
    const scenarioPath = `${project}/Checkout/case.feature`;
    const runPath = `${project}/test-run/smoke/nightly.yaml`;
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Checkout" } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: `${project}/Checkout`, file_name: "case", scenario_name: "Buy", description: "Purchase" } })).status()).toBe(201);
      expect((await request.post(`/api/runs/${project}/groups`, { data: { name: "smoke" } })).status()).toBe(201);
      expect((await request.post("/api/runs", { data: { project, group: "smoke", file_name: "nightly", name: "Nightly", case_paths: [scenarioPath] } })).status()).toBe(201);
      expect((await request.post(`/api/reports/${project}`, { data: { file_name: "buy-trend", title: "Buy trend", type: "case_trend", case_path: scenarioPath, run_paths: [runPath] } })).status()).toBe(201);
      await page.goto(`/?tab=reports&project=${encodeURIComponent(project)}`);
      await page.locator("tbody tr").filter({ hasText: "Buy trend" }).click();
      const queuedRuns = page.locator("details.report-source-list");
      await expect(queuedRuns).not.toHaveAttribute("open", "");
      await queuedRuns.locator("summary").click();
      await expect(page.locator(".report-source-row").filter({ hasText: "Nightly" })).toBeVisible();
      await expect(page.getByText(runPath, { exact: true })).toHaveCount(0);
      await page.getByRole("button", { name: "Remove Nightly" }).click();
      const addRun = page.locator("details.report-run-queue");
      await expect(addRun).not.toHaveAttribute("open", "");
      await expect(addRun.locator("summary")).toContainText("Add Run");
      await expect(addRun.locator("summary")).toContainText("1 available test runs");
      await addRun.locator("summary").click();
      await page.locator(".report-run-option").filter({ hasText: "Nightly" }).click();
      await expect(page.getByRole("button", { name: "Save", exact: true })).toBeEnabled();
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await expect(page.getByText("Saved", { exact: true })).toBeVisible();
      await queuedRuns.locator("summary").click();
      await page.locator(".report-source-row").filter({ hasText: "Nightly" }).click();
      await expect(page).toHaveURL(new RegExp(`tab=runs.*project=${project}.*run=smoke`));
      await expect(page.locator("select.case-status")).toHaveValue("PENDING");
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("renames a folder from the directory view", async ({ page, request }) => {
    const project = `pw_folder_rename_${Date.now()}`;
    const original = `${project}/Checkout`;
    const renamed = `${project}/Regression`;
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Checkout" } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: original, file_name: "case", scenario_name: "Case", description: "Purchase" } })).status()).toBe(201);
      await page.goto(`/?tab=directory&project=${encodeURIComponent(project)}&path=${encodeURIComponent(original)}`);
      await expect(page.locator("section.content .card-header strong").filter({ hasText: original })).toBeVisible();
      await page.getByRole("button", { name: "Rename folder", exact: true }).click();
      const renameFolder = page.getByRole("dialog");
      await renameFolder.getByLabel("Folder name").fill("Regression");
      await renameFolder.getByRole("button", { name: "Rename" }).click();
      await expect(page.locator("section.content .card-header strong").filter({ hasText: renamed })).toBeVisible();
      await expect(page.locator("tbody tr").filter({ hasText: "Case" })).toBeVisible();
      expect((await request.get(`/api/folders/${original}/contents`)).status()).toBe(404);
      expect((await request.get(`/api/folders/${renamed}/contents`)).status()).toBe(200);
      expect((await request.get(`/api/files/${renamed}/case.feature`)).status()).toBe(200);
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("creates enum kinds and entries inline and saves a display label", async ({ page, request }) => {
    const project = `pw_enums_${Date.now()}`;
    const alternateProject = `${project}_other`;
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: "", name: alternateProject } })).status()).toBe(201);
      await page.goto(`/?tab=enums&project=${encodeURIComponent(project)}`);
      await expect(page.getByText("Project enums", { exact: true })).toBeVisible();
      const projectPicker = page.getByLabel("Enum project");
      await expect(projectPicker).toBeEnabled();
      await expect(projectPicker.locator("option").filter({ hasText: alternateProject })).toBeAttached();
      await projectPicker.selectOption(alternateProject);
      await expect(projectPicker).toHaveValue(alternateProject);
      await projectPicker.selectOption(project);
      await page.getByPlaceholder("New kind ID").fill("priority");
      await page.getByRole("button", { name: "Add kind", exact: true }).click();
      const section = page.locator(".enum-section").filter({ hasText: "priority" });
      await expect(section).toBeVisible();
      await section.getByPlaceholder("Entry key").fill("p1");
      await section.getByPlaceholder("Display label").fill("High");
      await section.getByRole("button", { name: "Add entry", exact: true }).click();
      await expect(section.getByText("p1", { exact: true })).toBeVisible();
      await page.getByLabel("priority display label", { exact: true }).fill("Priority");
      const labelsResponse = page.waitForResponse((response) => response.url().endsWith(`/api/enums/${project}/kind-labels`) && response.request().method() === "PUT");
      await page.getByRole("button", { name: "Save kind labels", exact: true }).click();
      const saved = await labelsResponse;
      expect(saved.status()).toBe(200);
      await expect(saved.json()).resolves.toMatchObject({ priority: "Priority" });
    } finally {
      await request.delete(`/api/folders/${project}`);
      await request.delete(`/api/folders/${alternateProject}`);
    }
  });

  test("saves raw feature content, then renames and moves the file", async ({ page, request }) => {
    const project = `pw_mutations_${Date.now()}`;
    const source = `${project}/Source`;
    const target = `${project}/Target`;
    const originalPath = `${source}/case.feature`;
    const renamedPath = `${source}/renamed.feature`;
    const movedPath = `${target}/renamed.feature`;
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Source" } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Target" } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: source, file_name: "case", scenario_name: "Case", description: "Initial" } })).status()).toBe(201);
      await page.goto(`/?tab=directory&project=${encodeURIComponent(project)}&path=${encodeURIComponent(originalPath)}`);
      await page.getByRole("button", { name: "Raw", exact: true }).click();
      const editor = page.locator("textarea.editor");
      const changed = "@smoke\nFeature: Changed\n\nScenario: Changed case\n  Given a saved raw step\n";
      await editor.fill(changed);
      await page.getByRole("button", { name: "Save", exact: true }).click();
      await expect(page.getByText("Saved", { exact: true })).toBeVisible();
      expect(await (await request.get(`/api/files/${project}/Source/case.feature/raw`)).text()).toBe(changed);

      await page.goto(`/?tab=directory&project=${encodeURIComponent(project)}&path=${encodeURIComponent(source)}`);
      const originalRow = page.locator("tbody tr").filter({ hasText: "Changed case" });
      await expect(originalRow).toBeVisible();
      await originalRow.getByRole("button", { name: "Edit case.feature", exact: true }).click();
      const renameFeature = page.getByRole("dialog");
      await expect(renameFeature.locator(".editor-field")).toHaveCount(2);
      await renameFeature.getByLabel("Scenario name").fill("Renamed scenario");
      await renameFeature.getByLabel("Feature file name").fill("renamed");
      await renameFeature.getByRole("button", { name: "Save" }).click();
      const renamedRow = page.locator("tbody tr").filter({ hasText: "Renamed scenario" });
      await expect(renamedRow).toBeVisible();
      await renamedRow.click();
      await page.getByLabel("Move feature destination").selectOption(target);
      await page.getByRole("button", { name: "Move", exact: true }).click();
      await expect(page.locator("section.content .card-header strong").filter({ hasText: target })).toBeVisible();
      await expect(page.locator("tbody tr").filter({ hasText: "Renamed scenario" })).toBeVisible();
      expect((await request.get(`/api/files/${renamedPath}`)).status()).toBe(404);
      const moved = await request.get(`/api/files/${movedPath}`);
      expect(moved.status()).toBe(200);
      await expect(moved.json()).resolves.toMatchObject({ scenario: { name: "Renamed scenario" } });
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });

  test("handles clean reload, dirty conflict, and removal from external file changes", async ({ page, request }) => {
    const project = `pw_events_${Date.now()}`;
    const filePath = resolve("..", "project", project, "Checkout", "case.feature");
    try {
      expect((await request.post("/api/folders", { data: { parent: "", name: project } })).status()).toBe(201);
      expect((await request.post("/api/folders", { data: { parent: project, name: "Checkout" } })).status()).toBe(201);
      expect((await request.post("/api/files", { data: { parent: `${project}/Checkout`, file_name: "case", scenario_name: "Case", description: "Initial" } })).status()).toBe(201);
      await page.addInitScript(() => {
        const NativeEventSource = window.EventSource;
        class CapturingEventSource extends NativeEventSource {
          constructor(url: string | URL, config?: EventSourceInit) {
            super(url, config);
            (window as Window & { __tmsEventSource?: EventSource }).__tmsEventSource = this;
          }
        }
        window.EventSource = CapturingEventSource;
      });
      await page.goto(`/?tab=directory&project=${encodeURIComponent(project)}&path=${encodeURIComponent(`${project}/Checkout/case.feature`)}`);
      await expect(page.getByText(`${project}/Checkout/case.feature`, { exact: true })).toBeVisible();
      await page.waitForTimeout(700);
      await writeFile(filePath, "Feature: Updated\n\nScenario: Updated\n  Given an external change\n", "utf8");
      await page.evaluate(() => (window as Window & { __tmsEventSource?: EventSource }).__tmsEventSource?.dispatchEvent(new Event("change")));
      await expect(page.locator(".notice").filter({ hasText: "File was updated externally; the editor reloaded." })).toBeVisible({ timeout: 10000 });
      await page.getByRole("button", { name: "Raw", exact: true }).click();
      const editor = page.locator("textarea.editor");
      await editor.fill(`${await editor.inputValue()}\n# local draft`);
      await page.waitForTimeout(100);
      await writeFile(filePath, "Feature: Changed again\n\nScenario: Changed again\n  Given another external change\n", "utf8");
      await page.evaluate(() => (window as Window & { __tmsEventSource?: EventSource }).__tmsEventSource?.dispatchEvent(new Event("change")));
      await expect(page.locator(".notice").filter({ hasText: "File changed externally while you have unsaved changes." })).toBeVisible({ timeout: 10000 });
      await page.getByRole("button", { name: "Reload (discard mine)", exact: true }).click();
      await expect(page.locator("textarea.editor")).toHaveValue(/Changed again/);
      await page.waitForTimeout(200);
      await unlink(filePath);
      await page.evaluate(() => (window as Window & { __tmsEventSource?: EventSource }).__tmsEventSource?.dispatchEvent(new Event("change")));
      await expect(page.locator(".notice").filter({ hasText: "This file was removed on disk." })).toBeVisible({ timeout: 10000 });
      await page.getByRole("button", { name: "Discard", exact: true }).click();
      await expect(page.getByText("No test cases.", { exact: true })).toBeVisible();
    } finally {
      await request.delete(`/api/folders/${project}`);
    }
  });
});
