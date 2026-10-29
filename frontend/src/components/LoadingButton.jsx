import styles from "./LoadingButton.module.css";

const LoadingButton = () => {
  return (
    <div className={styles.loadingButton}>
      <div className={styles.loadingButtonInner}>
        <div className={styles.instanceChild} />
      </div>
      <img className={styles.loading1Icon} alt="" />
    </div>
  );
};

export default LoadingButton;
