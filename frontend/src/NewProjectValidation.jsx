import { useCallback } from 'react';
import {css} from "@emotion/css";



const NewProjectValidation = () => {
  	
  	const onInfoIconClick = useCallback(() => {
    		// Add your code here
  	}, []);
  	
  	return (
    		<div className={css`width: 100%;
height: 1024px;
position: relative;
background-color: var(--color-gray-100);
overflow: hidden;
text-align: left;
font-size: var(--fs-24);
color: var(--color-gray-200);
font-family: var(--font-inter);
`}>
    		<img className={css`position: absolute;
    		top: 245px;
    		left: 1079px;
    		width: 722px;
    		height: 722px;
    		flex-shrink: 0;
    		`} alt="" />
    		<div className={css`position: absolute;
    		top: 245px;
    		left: calc(50% - 141px);
    		font-size: 48px;
    		font-weight: 600;
    		text-align: center;
    		flex-shrink: 0;
    		`}>New Project</div>
    		<div className={css`position: absolute;
    		top: 390px;
    		left: 292px;
    		border-radius: 5px;
    		background-color: var(--color-lightgray);
    		border: 0.5px solid var(--color-gray-200);
    		box-sizing: border-box;
    		width: 856px;
    		height: 35px;
    		opacity: 0.8;
    		flex-shrink: 0;
    		`} />
    		<div className={css`position: absolute;
    		top: 395px;
    		left: 301px;
    		font-size: 20px;
    		display: inline-block;
    		width: 687px;
    		height: 24px;
    		flex-shrink: 0;
    		`}>https://github.com/your-username/invalid-link-click-to-change</div>
    		<div className={css`position: absolute;
    		top: 732px;
    		left: 657px;
    		width: 126px;
    		height: 64px;
    		flex-shrink: 0;
    		text-align: center;
    		font-size: 32px;
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
    		background-color: var(--color-coral-100);
    		`} />
                </div>
    		<b className={css`position: absolute;
    		width: 94px;
    		top: 20.31%;
    		left: 12.7%;
    		display: inline-block;
    		`}>Next</b>
            </div>
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
    		`} alt="" onClick={onInfoIconClick} />
    		<div className={css`position: absolute;
    		top: 48px;
    		left: 63px;
    		width: 200px;
    		height: 50.7px;
    		cursor: pointer;
    		`} onClick={onInfoIconClick}>
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
    		<div className={css`position: absolute;
    		top: 815px;
    		left: 681px;
    		font-weight: 100;
    		flex-shrink: 0;
    		`}>Cancel</div>
    		<div className={css`position: absolute;
    		top: 350px;
    		left: 292px;
    		font-weight: 600;
    		flex-shrink: 0;
    		`}>GitHub Repository URL</div>
        </div>);
};

export default NewProjectValidation ;
