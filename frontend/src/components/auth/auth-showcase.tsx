export function AuthShowcase() {
  return (
    <div className="relative hidden overflow-hidden bg-[#1A1B1E] md:flex md:flex-col md:justify-end md:p-16">
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full opacity-40"
        viewBox="0 0 600 800"
        fill="none"
        aria-hidden="true"
      >
        <g stroke="#B8863B" strokeWidth="1">
          <line x1="80" y1="120" x2="220" y2="200" />
          <line x1="220" y1="200" x2="180" y2="360" />
          <line x1="220" y1="200" x2="400" y2="160" />
          <line x1="400" y1="160" x2="480" y2="320" />
          <line x1="180" y1="360" x2="340" y2="440" />
          <line x1="340" y1="440" x2="480" y2="320" />
          <line x1="340" y1="440" x2="260" y2="600" />
          <line x1="260" y1="600" x2="440" y2="660" />
          <line x1="480" y1="320" x2="540" y2="500" />
          <line x1="540" y1="500" x2="440" y2="660" />
        </g>
        <g fill="#B8863B">
          <circle cx="80" cy="120" r="4" />
          <circle cx="220" cy="200" r="5" />
          <circle cx="400" cy="160" r="4" />
          <circle cx="180" cy="360" r="4" />
          <circle cx="480" cy="320" r="5" />
          <circle cx="340" cy="440" r="6" />
          <circle cx="260" cy="600" r="4" />
          <circle cx="540" cy="500" r="4" />
          <circle cx="440" cy="660" r="5" />
        </g>
      </svg>
      <div className="relative">
        <p className="font-display text-2xl font-medium leading-snug text-[#FAF8F4]">
          Every function, call,
          <br />
          and commit — mapped.
        </p>
        <p className="mt-3 max-w-xs font-mono text-xs text-[#FAF8F4]/50">
          GitBrain reads a repository once and remembers its architecture.
        </p>
      </div>
    </div>
  );
}
