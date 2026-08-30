import { useEffect, useRef } from "react";
import type { PointerEvent as ReactPointerEvent, ReactElement, ReactNode } from "react";

import "./holo-card.css";

export function HoloCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}): ReactElement {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(([entry]) => {
      node.classList.toggle("is-offscreen", !entry.isIntersecting);
    }, { threshold: 0.05 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  function setVars(x: number, y: number, on: number): void {
    const node = ref.current;
    if (!node) return;
    node.style.setProperty("--holo-x", x.toFixed(4));
    node.style.setProperty("--holo-y", y.toFixed(4));
    node.style.setProperty("--holo-on", on.toFixed(4));
    node.classList.toggle("is-tracking", on > 0);
  }

  function onPointerMove(event: ReactPointerEvent<HTMLDivElement>): void {
    const node = ref.current;
    if (!node) return;
    const box = node.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) return;
    const x = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width));
    const y = Math.min(1, Math.max(0, (event.clientY - box.top) / box.height));
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    setVars(x, y, 1);
  }

  return (
    <div className="holo-card-stage">
      <div
        ref={ref}
        className={className ? `holo-card ${className}` : "holo-card"}
        onPointerEnter={onPointerMove}
        onPointerMove={onPointerMove}
        onPointerLeave={() => setVars(0.5, 0.5, 0)}
      >
        <span className="holo-card-foil" aria-hidden="true" />
        <span className="holo-card-glare" aria-hidden="true" />
        <span className="holo-card-spark" aria-hidden="true" />
        <div className="holo-card-face">{children}</div>
      </div>
    </div>
  );
}
