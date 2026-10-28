import { useCallback } from 'react';
import {css} from "@emotion/css";
import {useNavigate} from "react-router-dom";



const Landing = () => {
  	const navigate = useNavigate();
  	
  	const onInfoIconClick = useCallback(() => {
    		// Add your code here
  	}, []);
  	
  	
  	const onGitGalleryLogoContainerClick = useCallback(() => {
    		navigate("/");
  	}, [navigate]);
  	
  	return (
    		<div className={css`width: 100%;
height: 1024px;
position: relative;
background-color: var(--color-gray-100);
overflow: hidden;
text-align: left;
font-size: var(--fs-24);
color: var(--color-gray-100);
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
    		top: calc(50% - 223px);
    		left: calc(50% - 428px);
    		width: 856px;
    		height: 82px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		flex-shrink: 0;
    		font-size: 96px;
    		color: var(--color-indigo);
    		font-family: var(--font-jetbrains-mono);
    		`}>
    		<b className={css`position: relative;
    		letter-spacing: -1.2px;
    		line-height: var(--lh-48);
    		display: none;
    		`}>
    		<span className={css`line-height: var(--lh-48);
    		`}>git</span>
    		<span className={css`color: var(--color-coral-200);
    		line-height: var(--lh-48);
    		`}>gallery</span>
                </b>
    		<img className={css`width: 336px;
    		height: 82px;
    		position: relative;
    		`} alt="" />
            </div>
    		<div className={css`position: absolute;
    		top: calc(50% - 128px);
    		left: calc(50% - 428px);
    		width: 672px;
    		height: 32px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: 8px var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		flex-shrink: 0;
    		color: var(--color-slategray);
    		`}>
    		<div className={css`position: relative;
    		line-height: 24px;
    		`}>{`Visual commit history for designers & stakeholders`}</div>
            </div>
    		<div className={css`position: absolute;
    		width: 59.44%;
    		right: 20.28%;
    		bottom: -147px;
    		left: 20.28%;
    		height: var(--height-459);
    		flex-shrink: 0;
    		color: var(--color-gray-200);
    		font-family: var(--font-jetbrains-mono);
    		`}>
    		<div className={css`position: absolute;
    		width: 46.73%;
    		right: 0%;
    		bottom: 0px;
    		left: 53.27%;
    		height: var(--height-459);
    		`}>
    		<div className={css`position: absolute;
    		width: 100%;
    		right: 0%;
    		bottom: 0px;
    		left: 0%;
    		border-radius: 69px;
    		background: var(--gradient-1);
    		border: 5px solid transparent;
    		box-sizing: border-box;
    		height: var(--height-459);
    		`} />
    		<div className={css`position: absolute;
    		width: 68.5%;
    		right: 21.5%;
    		bottom: 389px;
    		left: 10%;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<b className={css`position: relative;
    		line-height: var(--lh-20);
    		`}>AI-Powered Insights</b>
                    </div>
    		<div className={css`position: absolute;
    		width: 68.5%;
    		right: 21.5%;
    		bottom: 286px;
    		left: 10%;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-12) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		font-size: var(--fs-16);
    		color: var(--color-slategray);
    		font-family: var(--font-inter);
    		`}>
    		<div className={css`width: 274px;
    		position: relative;
    		line-height: 22.75px;
    		display: inline-block;
    		`}>AI groups commits into milestones, highlights what changed visually, and explains each change in plain language.</div>
                    </div>
                </div>
    		<div className={css`position: absolute;
    		width: 46.73%;
    		right: 53.27%;
    		bottom: 0px;
    		left: 0%;
    		height: var(--height-459);
    		`}>
    		<div className={css`position: absolute;
    		width: 100%;
    		right: 0%;
    		bottom: 0px;
    		left: 0%;
    		border-radius: 69px;
    		background: var(--gradient-1);
    		border: 5px solid transparent;
    		box-sizing: border-box;
    		height: var(--height-459);
    		`} />
    		<div className={css`position: absolute;
    		width: 68.5%;
    		right: 23.25%;
    		bottom: 389px;
    		left: 8.25%;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<b className={css`position: relative;
    		line-height: var(--lh-20);
    		`}>Visual Timeline</b>
                    </div>
    		<div className={css`position: absolute;
    		width: 68.5%;
    		right: 23.25%;
    		bottom: 287px;
    		left: 8.25%;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-12) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		font-size: var(--fs-16);
    		color: var(--color-slategray);
    		font-family: var(--font-inter);
    		`}>
    		<div className={css`width: 274px;
    		position: relative;
    		line-height: 22.75px;
    		display: inline-block;
    		`}>Browse every commit as a visual screenshot, not a wall of diffs. Understand the evolution of your project at a glance.</div>
                    </div>
                </div>
            </div>
    		<div className={css`position: absolute;
    		top: calc(50% + 55px);
    		left: calc(50% - 136px);
    		width: 272px;
    		height: var(--height-64);
    		flex-shrink: 0;
    		font-size: var(--fs-36);
    		`}>
    		<div className={css`position: absolute;
    		top: 0px;
    		left: 0px;
    		border-radius: var(--br-10);
    		background-color: var(--color-coral-100);
    		width: 272px;
    		height: var(--height-64);
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-10);
    		background-color: var(--color-slategray);
    		`} />
                </div>
    		<b className={css`position: absolute;
    		top: 10px;
    		left: 25px;
    		`}>View Gallery</b>
            </div>
    		<div className={css`position: absolute;
    		top: calc(50% - 32px);
    		left: calc(50% - 136px);
    		width: 272px;
    		height: var(--height-64);
    		flex-shrink: 0;
    		font-size: var(--fs-36);
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
    		top: 15.63%;
    		left: 11.03%;
    		`}>New Project</b>
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
    		`} onClick={onGitGalleryLogoContainerClick}>
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
        </div>);
};

export default Landing ;
