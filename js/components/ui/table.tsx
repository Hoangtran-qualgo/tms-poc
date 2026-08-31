import * as React from "react";
import { cn } from "@/src/lib/utils";

const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(({ className, ...props }, ref) => <table ref={ref} className={cn("table", className)} {...props} />);
Table.displayName = "Table";

export { Table };
