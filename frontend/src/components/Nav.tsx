"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "ホーム" },
  { href: "/chat", label: "Text / RAG" },
  { href: "/lab", label: "AI Lab" },
  { href: "/documents", label: "Documents" },
  { href: "/image", label: "Image" },
  { href: "/embedding", label: "Embedding" },
  { href: "/guardrails", label: "Guardrails" },
  { href: "/prompts", label: "Prompts" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/agents", label: "Agents" },
  { href: "/ops", label: "Ops" },
  { href: "/gcp", label: "GCP" },
  { href: "/credit", label: "信用情報" },
  { href: "/tests", label: "Tests" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="nav">
      <div className="brand">
        Bedrock<span>KB</span>
      </div>
      <nav className="nav-links">
        {links.map((l) => (
          <Link key={l.href} href={l.href} className={pathname === l.href ? "active" : undefined}>
            {l.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
