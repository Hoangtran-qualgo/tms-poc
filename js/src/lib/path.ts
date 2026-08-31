const FORBIDDEN_SEGMENT_CHARS = new Set(["/", "\\", ":", "*", "?", '"', "<", ">", "|"]);

export class PathValidationError extends Error {}

export function validateLogicalSegments(segments: string[]): void {
  for (const segment of segments) {
    if (!segment) throw new PathValidationError("Empty path segment.");
    if (segment === "." || segment === "..") {
      throw new PathValidationError(`Disallowed path segment: '${segment}'`);
    }
    for (const character of segment) {
      if (FORBIDDEN_SEGMENT_CHARS.has(character) || character.codePointAt(0)! < 0x20) {
        throw new PathValidationError(`Forbidden character '${character}' in path segment: '${segment}'`);
      }
    }
  }
}
