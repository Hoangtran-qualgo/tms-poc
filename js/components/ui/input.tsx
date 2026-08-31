import * as React from "react";
import { cn } from "@/src/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(({ className, type, ...props }, ref) => (
  <input ref={ref} type={type} className={cn("input", className)} {...props} />
));
Input.displayName = "Input";

export { Input };
