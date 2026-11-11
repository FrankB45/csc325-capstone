import styles from "./ArrowButton.module.css";

/** Coral triangle used to scroll the timeline. direction: "left" | "right" */
const ArrowButton = ({ direction, onClick, disabled = false, label }) => (
  <button
    type="button"
    className={`${styles.arrow} ${styles[direction]}`}
    onClick={onClick}
    disabled={disabled}
    aria-label={label ?? (direction === "left" ? "Scroll timeline left" : "Scroll timeline right")}
  />
);

export default ArrowButton;
