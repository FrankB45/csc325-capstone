import styles from "./ModeToggle.module.css";

const OPTIONS = [
  { value: "standard", label: "Standard" },
  { value: "compare", label: "Compare" },
];

const ModeToggle = ({ value, onChange }) => (
  <div className={styles.toggle} role="group" aria-label="Timeline mode">
    {OPTIONS.map((o) => (
      <button
        key={o.value}
        type="button"
        className={`${styles.option} ${value === o.value ? styles.active : ""}`}
        aria-pressed={value === o.value}
        onClick={() => onChange(o.value)}
      >
        {o.label}
      </button>
    ))}
  </div>
);

export default ModeToggle;
