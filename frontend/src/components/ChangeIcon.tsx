/** Small "change detection" identifier (two overlapping squares + delta), secondary to the Land AI mark. */
export default function ChangeIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" className="flame-icon"
         fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="12" height="12" rx="2" />
      <path d="M9 21h10a2 2 0 0 0 2-2V9" />
      <path d="M9 11l2-4 2 4z" />
    </svg>
  );
}
