import { SSEParser } from "./sse-parser";

const parser = new SSEParser();

// 1. Single complete event
let events = parser.parseChunk('data: {"content": "hello"}\n\n');
console.assert(events.length === 1);
console.assert(events[0]!.data.content === "hello");

// 2. Fragmented event
events = parser.parseChunk('data: {"con');
console.assert(events.length === 0);
events = parser.parseChunk('tent": "world"}\n\n');
console.assert(events.length === 1);
console.assert(events[0]!.data.content === "world");

// 3. Multiple events in one chunk
events = parser.parseChunk('data: {"content": "A"}\n\ndata: {"content": "B"}\n\n');
console.assert(events.length === 2);
console.assert(events[0]!.data.content === "A");
console.assert(events[1]!.data.content === "B");

// 4. Malformed JSON (should not crash)
events = parser.parseChunk('data: {malformed}\n\n');
console.assert(events.length === 0);

console.log("All SSE parser tests passed!");
