import { useCallback } from 'react';
import {css} from "@emotion/css";



const NewProjectTimelineLoading = () => {
  	
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
font-size: 36px;
color: var(--color-gray-200);
font-family: var(--font-inter);
`}>
    		<div className={css`position: absolute;
    		top: 0px;
    		left: 0px;
    		background-color: var(--color-gray-200);
    		width: 1440px;
    		height: 142px;
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
    		<b className={css`position: absolute;
    		top: 490px;
    		left: 563px;
    		`}>Creating Timeline</b>
    		<img className={css`position: absolute;
    		width: 6.39%;
    		top: 525px;
    		right: 46.81%;
    		left: 46.81%;
    		max-width: 100%;
    		overflow: hidden;
    		height: 92px;
    		object-fit: cover;
    		`} alt="" />
        </div>);
};

export default NewProjectTimelineLoading ;
