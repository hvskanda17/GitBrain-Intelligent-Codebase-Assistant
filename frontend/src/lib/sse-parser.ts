export type SSEEvent = {
  data: any;
};

export class SSEParser {
  private buffer = "";

  /**
   * Parse a chunk of string from the stream.
   * Returns an array of parsed events.
   */
  parseChunk(chunk: string): SSEEvent[] {
    this.buffer += chunk;
    const events: SSEEvent[] = [];

    let newlineIdx: number;
    // SSE events are separated by double newline \n\n
    while ((newlineIdx = this.buffer.indexOf("\n\n")) !== -1) {
      const eventStr = this.buffer.slice(0, newlineIdx).trim();
      this.buffer = this.buffer.slice(newlineIdx + 2);

      if (!eventStr) continue;

      // Extract lines
      const lines = eventStr.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataStr = line.slice(6);
          try {
            events.push({ data: JSON.parse(dataStr) });
          } catch (e) {
            // Ignore malformed JSON per SSE parser standards for this specific app
          }
        }
      }
    }

    return events;
  }
}
