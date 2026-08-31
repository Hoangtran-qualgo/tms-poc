const HTML_HEADERS = { "content-type": "text/html; charset=utf-8" };

function html(status: number, title: string, heading: string, message: string): Response {
  return new Response(
    `<!doctype html>\n<html lang=en>\n<title>${status} ${title}</title>\n<h1>${heading}</h1>\n<p>${message}</p>\n`,
    { status, headers: HTML_HEADERS },
  );
}

/** Flask/Werkzeug-style default response for an unmatched route. */
export function defaultNotFound(): Response {
  return html(404, "Not Found", "Not Found", "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.");
}

/** Flask/Werkzeug-style default response for an unsupported method. */
export function defaultMethodNotAllowed(): Response {
  return html(405, "Method Not Allowed", "Method Not Allowed", "The method is not allowed for the requested URL.");
}
