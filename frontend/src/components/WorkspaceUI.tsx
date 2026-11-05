import {
  useEffect,
  useId,
  useRef,
  type CSSProperties,
  type ReactNode,
  type ButtonHTMLAttributes,
} from "react";
import {
  Activity,
  ArrowRight,
  Loader2,
  Plus,
  type LucideIcon,
} from "lucide-react";

export function Brand() {
  return (
    <span className="brand">
      <span className="brand-mark">
        <Activity size={25} strokeWidth={2.4} />
      </span>
      <span className="brand-name">
        Clinical<span>AI</span>
        <small>CLINICAL INTELLIGENCE</small>
      </span>
    </span>
  );
}

export function Button({
  children,
  busy = false,
  variant = "primary",
  className = "",
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  busy?: boolean;
  variant?: "primary" | "secondary" | "danger";
}) {
  return (
    <button
      {...props}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={`button button-${variant} ${className}`}
    >
      {busy ? <Loader2 className="spin" size={16} aria-hidden="true" /> : null}
      {children}
    </button>
  );
}

export function Field({
  label,
  optional = false,
  children,
  hint,
}: {
  label: string;
  optional?: boolean;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>
        {label}
        {optional ? (
          <small>Optional</small>
        ) : (
          <span className="required-mark" aria-label="required">
            {" "}
            *
          </span>
        )}
      </span>
      {children}
      {hint ? <small className="field-hint">{hint}</small> : null}
    </label>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "error";
}) {
  return (
    <span className={`badge badge-${tone}`}>
      <span className="badge-dot" aria-hidden="true" />
      {children}
    </span>
  );
}

export function CardHeading({
  icon: Icon,
  title,
  description,
  trailing,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  trailing?: ReactNode;
}) {
  return (
    <div className="card-heading">
      <span className="icon-tile">
        <Icon size={20} aria-hidden="true" />
      </span>
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {trailing}
    </div>
  );
}

export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current;
    if (
      !element ||
      !window.IntersectionObserver ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    )
      return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          element.classList.add("reveal-enter");
          observer.disconnect();
        }
      },
      { threshold: 0.08 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      className={`reveal ${className}`}
      style={{ "--reveal-delay": `${delay}ms` } as CSSProperties}
    >
      {children}
    </div>
  );
}

export function IntelligenceArt({ className = "" }: { className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <div className={`intelligence-art ${className}`} aria-hidden="true">
      <svg viewBox="0 0 420 280" fill="none">
        <defs>
          <radialGradient id={id}>
            <stop stopColor="#53c7c4" stopOpacity=".23" />
            <stop offset="1" stopColor="#53c7c4" stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse cx="230" cy="140" rx="190" ry="140" fill={`url(#${id})`} />
        <g stroke="currentColor" strokeOpacity=".15">
          <path d="M40 160 100 90 170 115 220 45 285 100 365 70M100 90 120 210 170 115 245 165 285 100 340 210M40 160 120 210 200 245 245 165 340 210 390 140 365 70M170 115 285 100M220 45 245 165M100 90 245 165M285 100 390 140" />
          <circle cx="245" cy="140" r="93" strokeDasharray="3 7" />
          <circle cx="245" cy="140" r="65" />
          <path
            d="M160 143h38l13-23 19 43 19-60 18 40h57"
            strokeOpacity=".65"
            strokeWidth="2"
          />
        </g>
        {[
          [40, 160],
          [100, 90],
          [170, 115],
          [220, 45],
          [285, 100],
          [365, 70],
          [120, 210],
          [200, 245],
          [245, 165],
          [340, 210],
          [390, 140],
        ].map(([cx, cy], i) => (
          <g key={i}>
            <circle cx={cx} cy={cy} r="8" fill="currentColor" opacity=".05" />
            <circle
              cx={cx}
              cy={cy}
              r={i % 3 === 0 ? 3.5 : 2.5}
              fill="currentColor"
              opacity=".55"
            />
          </g>
        ))}
        <circle
          cx="245"
          cy="140"
          r="112"
          stroke="currentColor"
          strokeOpacity=".08"
        />
      </svg>
    </div>
  );
}

export function AnimatedBackground() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    function update() {
      frame = 0;
      ref.current?.style.setProperty(
        "--scroll-offset",
        `${Math.min(window.scrollY, 1200)}px`,
      );
    }
    function scroll() {
      if (!media.matches && !frame) frame = requestAnimationFrame(update);
    }
    window.addEventListener("scroll", scroll, { passive: true });
    function preference() {
      if (media.matches)
        ref.current?.style.setProperty("--scroll-offset", "0px");
      else scroll();
    }
    media.addEventListener("change", preference);
    scroll();
    return () => {
      window.removeEventListener("scroll", scroll);
      media.removeEventListener("change", preference);
      cancelAnimationFrame(frame);
    };
  }, []);
  return (
    <div ref={ref} className="ambient-background" aria-hidden="true">
      <div className="ambient-light" />
      <div className="ambient-network">
        <IntelligenceArt />
      </div>
    </div>
  );
}

export function SaveButton({
  busy,
  disabled,
  children,
}: {
  busy: boolean;
  disabled: boolean;
  children: ReactNode;
}) {
  return (
    <Button type="submit" busy={busy} disabled={disabled}>
      <Plus size={16} aria-hidden="true" />
      {busy ? "Saving…" : children}
    </Button>
  );
}

export function NextButton({
  onClick,
  children,
}: {
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Button type="button" variant="secondary" onClick={onClick}>
      {children}
      <ArrowRight size={16} aria-hidden="true" />
    </Button>
  );
}
