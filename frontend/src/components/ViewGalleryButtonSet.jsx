import styles from "./ViewGalleryButtonSet.module.css";

const ViewGalleryButtonSet = () => {
  return (
    <div className={styles.viewGalleryButton}>
      <div className={styles.property1viewGalleryPrope}>
        <div className={styles.viewGalleryButtonInner}>
          <div className={styles.instanceChild} />
        </div>
        <b className={styles.viewGallery}>View Gallery</b>
      </div>
      <div className={styles.property1viewGalleryPrope2}>
        <div className={styles.viewGalleryButtonChild}>
          <div className={styles.instanceItem} />
        </div>
        <b className={styles.viewGallery2}>
          View Gallery
          <br />
        </b>
      </div>
    </div>
  );
};

export default ViewGalleryButtonSet;
