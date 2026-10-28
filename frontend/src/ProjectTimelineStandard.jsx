import { useCallback } from 'react';
import {css} from "@emotion/css";



const ProjectTimelineStandard = () => {
  	
  	const onBackToGalleryClick = useCallback(() => {
    		// Add your code here
  	}, []);
  	
  	return (
    		<div className={css`width: 100%;
height: 1024px;
position: relative;
background-color: var(--color-gray-100);
overflow: hidden;
text-align: center;
font-size: var(--fs-20);
color: var(--color-gray-200);
font-family: var(--font-inter);
`}>
    		<div className={css`position: absolute;
    		top: 686px;
    		left: 0px;
    		border-radius: 5px;
    		background: linear-gradient(180deg, rgba(215, 203, 214, 0), rgba(197, 179, 195, 0.3) 25.48%, rgba(179, 155, 175, 0.5) 49.52%, rgba(215, 203, 214, 0.3) 75.96%, rgba(215, 203, 214, 0));
    		width: 1442px;
    		height: 338px;
    		flex-shrink: 0;
    		`} />
    		<img className={css`position: absolute;
    		top: 195px;
    		left: 316px;
    		width: 808px;
    		height: 809px;
    		flex-shrink: 0;
    		`} alt="" />
    		<b className={css`position: absolute;
    		top: 181px;
    		left: 38px;
    		font-size: var(--fs-24);
    		text-align: left;
    		cursor: pointer;
    		flex-shrink: 0;
    		`} onClick={onBackToGalleryClick}>{`< Back to Gallery`}</b>
    		<div className={css`position: absolute;
    		top: 0px;
    		left: 0px;
    		background-color: var(--color-gray-200);
    		width: 1440px;
    		height: 142px;
    		flex-shrink: 0;
    		`}>
    		<img className={css`position: absolute;
    		top: 46px;
    		right: 60px;
    		width: 53px;
    		height: 53px;
    		cursor: pointer;
    		`} alt="" onClick={onBackToGalleryClick} />
    		<div className={css`position: absolute;
    		top: 48px;
    		left: 63px;
    		width: 200px;
    		height: 50.7px;
    		cursor: pointer;
    		`} onClick={onBackToGalleryClick}>
    		<img className={css`position: absolute;
    		top: 13.9px;
    		left: 57.56px;
    		width: 142.4px;
    		height: 27.5px;
    		`} alt="" />
    		<img className={css`position: absolute;
    		top: 0px;
    		left: 0px;
    		width: 50.7px;
    		height: 50.7px;
    		`} alt="" />
                </div>
            </div>
    		<img className={css`position: absolute;
    		top: 823px;
    		left: 107px;
    		width: 1224px;
    		height: 12px;
    		object-fit: contain;
    		flex-shrink: 0;
    		`} alt="" />
    		<img className={css`position: absolute;
    		top: 788px;
    		left: 17px;
    		width: 50px;
    		height: 70px;
    		object-fit: contain;
    		flex-shrink: 0;
    		`} alt="" />
    		<img className={css`position: absolute;
    		top: 788px;
    		left: 1372px;
    		width: 50px;
    		height: 70px;
    		object-fit: contain;
    		flex-shrink: 0;
    		`} alt="" />
    		<div className={css`position: absolute;
    		top: 805px;
    		left: 79px;
    		width: var(--width-35);
    		height: var(--height-35);
    		overflow: hidden;
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-50);
    		background-color: var(--color-slategray);
    		`} />
            </div>
    		<div className={css`position: absolute;
    		top: 805px;
    		left: 492px;
    		width: var(--width-35);
    		height: var(--height-35);
    		overflow: hidden;
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-50);
    		background-color: var(--color-slategray);
    		`} />
            </div>
    		<div className={css`position: absolute;
    		top: 805px;
    		left: 293px;
    		width: var(--width-35);
    		height: var(--height-35);
    		overflow: hidden;
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-50);
    		background-color: var(--color-slategray);
    		`} />
            </div>
    		<div className={css`position: absolute;
    		top: 805px;
    		left: 692px;
    		width: var(--width-35);
    		height: var(--height-35);
    		overflow: hidden;
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-50);
    		background-color: var(--color-slategray);
    		`} />
            </div>
    		<div className={css`position: absolute;
    		top: 805px;
    		left: 891px;
    		width: var(--width-35);
    		height: var(--height-35);
    		overflow: hidden;
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-50);
    		background-color: var(--color-slategray);
    		`} />
            </div>
    		<div className={css`position: absolute;
    		top: 805px;
    		left: 1091px;
    		width: var(--width-35);
    		height: var(--height-35);
    		overflow: hidden;
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-50);
    		background-color: var(--color-slategray);
    		`} />
            </div>
    		<div className={css`position: absolute;
    		top: 805px;
    		left: 1325px;
    		width: var(--width-35);
    		height: var(--height-35);
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-50);
    		background-color: var(--color-slategray-200);
    		`} />
            </div>
    		<div className={css`position: absolute;
    		top: 182px;
    		left: 1154px;
    		width: 226px;
    		height: 45px;
    		flex-shrink: 0;
    		font-size: var(--fs-24);
    		color: var(--color-gray-100);
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-10);
    		background-color: var(--color-gray-100);
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-10);
    		background-color: var(--color-coral);
    		`} />
                </div>
    		<b className={css`position: absolute;
    		height: 60%;
    		width: 173px;
    		top: 20%;
    		left: 2.21%;
    		display: inline-block;
    		`}>Sync Updates</b>
    		<img className={css`position: absolute;
    		height: 58.22%;
    		width: 11.19%;
    		top: 22.22%;
    		right: 6.95%;
    		bottom: 19.56%;
    		left: 81.86%;
    		max-width: 100%;
    		overflow: hidden;
    		max-height: 100%;
    		`} alt="" />
            </div>
    		<div className={css`position: absolute;
    		top: 237px;
    		left: 1190px;
    		font-size: 16px;
    		font-weight: 500;
    		color: var(--color-black);
    		flex-shrink: 0;
    		`}>Last sync: 1 min ago</div>
    		<img className={css`position: absolute;
    		top: 314px;
    		left: 328px;
    		width: 788px;
    		height: 446px;
    		object-fit: cover;
    		flex-shrink: 0;
    		`} alt="" />
    		<div className={css`position: absolute;
    		top: 957px;
    		left: 18px;
    		width: 206px;
    		height: 44px;
    		cursor: pointer;
    		flex-shrink: 0;
    		text-align: left;
    		color: var(--color-gray-100);
    		`} onClick={onBackToGalleryClick}>
    		<div className={css`position: absolute;
    		top: 0px;
    		left: 0px;
    		border-radius: var(--br-10);
    		background: rgba(118, 120, 117, 0.5), #fff;
    		width: 206px;
    		height: 44px;
    		`} />
    		<div className={css`position: absolute;
    		top: 0px;
    		left: 0px;
    		border-radius: var(--br-10);
    		background-color: var(--color-coral);
    		width: 108px;
    		height: 44px;
    		`} />
    		<b className={css`position: absolute;
    		top: 10px;
    		left: 8px;
    		`}>Standard</b>
    		<b className={css`position: absolute;
    		top: 10px;
    		left: 111px;
    		color: var(--color-gray-400);
    		`}>Compare</b>
            </div>
    		<b className={css`position: absolute;
    		top: 858px;
    		left: 1244px;
    		display: inline-block;
    		width: 198px;
    		height: 102px;
    		flex-shrink: 0;
    		`}>9/30/26<br/>(a7c91e4)<br/><br/></b>
    		<div className={css`position: absolute;
    		top: 213px;
    		left: 38px;
    		width: 317px;
    		height: 39px;
    		flex-shrink: 0;
    		font-size: 32px;
    		`}>
    		<div className={css`position: absolute;
    		top: 0px;
    		left: 0px;
    		font-weight: 600;
    		background: linear-gradient(91.63deg, #f7b32b, var(--color-coral));
    		-webkit-background-clip: text;
    		-webkit-text-fill-color: transparent;
    		`}>Personal Website</div>
    		<img className={css`position: absolute;
    		top: 0px;
    		left: 278px;
    		width: 39px;
    		height: 39px;
    		`} alt="" />
            </div>
    		<b className={css`position: absolute;
    		top: 858px;
    		left: 1028px;
    		display: inline-block;
    		width: 161px;
    		height: 102px;
    		flex-shrink: 0;
    		`}>9/28/26<br/>(b2f6d83)</b>
    		<b className={css`position: absolute;
    		top: 858px;
    		left: 858px;
    		flex-shrink: 0;
    		`}>9/25/26<br/>(c84a1b9)</b>
    		<b className={css`position: absolute;
    		top: 858px;
    		left: 669px;
    		flex-shrink: 0;
    		`}>9/22/26<br/>(d19e5f2)</b>
    		<b className={css`position: absolute;
    		top: 858px;
    		left: 458px;
    		flex-shrink: 0;
    		`}>9/19/26<br/>(e73b0c6)</b>
    		<b className={css`position: absolute;
    		top: 858px;
    		left: 263px;
    		flex-shrink: 0;
    		`}>9/16/26<br/>(f5a28d1)</b>
    		<b className={css`position: absolute;
    		top: 858px;
    		left: 44px;
    		flex-shrink: 0;
    		`}>9/12/26<br/>(0b6c4e8)</b>
    		<div className={css`position: absolute;
    		top: 858px;
    		left: 893px;
    		width: 532px;
    		height: 180px;
    		flex-shrink: 0;
    		font-size: 14px;
    		color: var(--color-gray-100);
    		font-family: var(--font-dm-sans);
    		`}>
    		<div className={css`position: absolute;
    		top: 116px;
    		left: 232px;
    		border-radius: var(--br-10);
    		background-color: var(--color-slategray-100);
    		width: 300px;
    		height: 64px;
    		`}>
    		<div className={css`position: absolute;
    		top: 28px;
    		left: 20px;
    		border-radius: 16777200px;
    		background-color: var(--color-coral);
    		width: 8px;
    		height: 8px;
    		`} />
    		<div className={css`position: absolute;
    		top: 22px;
    		left: 36px;
    		line-height: 20px;
    		font-weight: 500;
    		`}>AI Assistant</div>
                </div>
            </div>
        </div>);
};

export default ProjectTimelineStandard ;
