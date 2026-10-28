import {css} from "@emotion/css";



const CommitOverlay = () => {
  	return (
    		<div className={css`width: 100%;
height: 808px;
position: relative;
overflow: hidden;
`}>
    		<img className={css`position: absolute;
    		top: 58px;
    		left: 27px;
    		width: 1233px;
    		height: 692px;
    		object-fit: cover;
    		`} alt="" />
    		<img className={css`position: absolute;
    		top: 0px;
    		left: 1210px;
    		width: 50px;
    		height: 50px;
    		object-fit: cover;
    		`} alt="" />
        </div>);
};

export default CommitOverlay ;
