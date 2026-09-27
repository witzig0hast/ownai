export type MessageSegment = { type: "text"; value: string } | { type: "code"; language: string; value: string };

const CODE_FENCE = /```(\w*)\n([\s\S]*?)```/g;

/** Splits a message's raw content into plain-text and fenced-code segments, so code blocks can
 * get their own renderer (CodeBlock) instead of being shown as part of one big plaintext blob.
 * Deliberately minimal - no full Markdown parsing (lists, bold, links, ...), just enough to find
 * ```lang\n...\n``` fences for the Code Interpreter feature. */
export function parseMessageContent(content: string): MessageSegment[] {
  const segments: MessageSegment[] = [];
  let lastIndex = 0;

  for (const match of content.matchAll(CODE_FENCE)) {
    const [fullMatch, language, code] = match;
    const start = match.index ?? 0;
    if (start > lastIndex) {
      segments.push({ type: "text", value: content.slice(lastIndex, start) });
    }
    segments.push({ type: "code", language: language.toLowerCase(), value: code.replace(/\n$/, "") });
    lastIndex = start + fullMatch.length;
  }

  if (lastIndex < content.length) {
    segments.push({ type: "text", value: content.slice(lastIndex) });
  }

  return segments.length > 0 ? segments : [{ type: "text", value: content }];
}
