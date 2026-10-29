import { useCallback } from 'react';
import {css} from "@emotion/css";



const NewProjectSetup = () => {
  	
  	const onInfoIconClick = useCallback(() => {
    		// Add your code here
  	}, []);
  	
  	return (
    		<div className={css`width: 100%;
height: 1502px;
position: relative;
background-color: var(--color-gray-100);
overflow: hidden;
text-align: left;
font-size: var(--fs-16);
color: var(--color-black);
font-family: var(--font-inter);
`}>
    		<img className={css`position: absolute;
    		top: 232px;
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
    		color: var(--color-gray-200);
    		text-align: center;
    		flex-shrink: 0;
    		`}>New Project</div>
    		<div className={css`position: absolute;
    		top: 390px;
    		left: 292px;
    		border-radius: var(--br-5);
    		background-color: var(--color-lightgray);
    		border: var(--border-1);
    		box-sizing: border-box;
    		width: 856px;
    		height: 35px;
    		opacity: var(--opacity-0_8);
    		flex-shrink: 0;
    		`} />
    		<div className={css`position: absolute;
    		top: 395px;
    		left: 301px;
    		font-size: var(--fs-20);
    		color: var(--color-gray-300);
    		display: inline-block;
    		width: 687px;
    		height: var(--height-24);
    		flex-shrink: 0;
    		`}>https://github.com/your-username/invalid-link-click-to-change</div>
    		<div className={css`position: absolute;
    		top: 1257px;
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
    		top: 1340px;
    		left: 681px;
    		font-size: var(--fs-24);
    		font-weight: 100;
    		color: var(--color-gray-200);
    		flex-shrink: 0;
    		`}>Cancel</div>
    		<div className={css`position: absolute;
    		top: 350px;
    		left: 292px;
    		font-size: var(--fs-24);
    		font-weight: 600;
    		color: var(--color-gray-200);
    		flex-shrink: 0;
    		`}>GitHub Repository URL</div>
    		<div className={css`position: absolute;
    		top: 519px;
    		left: 292px;
    		border-radius: var(--br-5);
    		background-color: var(--color-lightgray);
    		border: var(--border-1);
    		box-sizing: border-box;
    		width: 855px;
    		height: 35px;
    		opacity: var(--opacity-0_8);
    		flex-shrink: 0;
    		`} />
    		<div className={css`position: absolute;
    		top: 524px;
    		left: 302px;
    		font-size: var(--fs-20);
    		color: var(--color-gray-200);
    		display: inline-block;
    		width: 820px;
    		height: var(--height-24);
    		flex-shrink: 0;
    		`}>Personal Website</div>
    		<div className={css`position: absolute;
    		top: 486px;
    		left: 292px;
    		font-size: var(--fs-24);
    		font-weight: 600;
    		color: var(--color-gray-200);
    		display: flex;
    		align-items: center;
    		width: 149px;
    		flex-shrink: 0;
    		`}>Project Title</div>
    		<div className={css`position: absolute;
    		top: 591px;
    		left: 413px;
    		border-radius: var(--br-10);
    		background: linear-gradient(-44.38deg, var(--color-coral-100) 0.65%, #f7b32b) border-box;
    		border: 10px solid transparent;
    		box-sizing: border-box;
    		width: 613px;
    		height: 320px;
    		overflow: hidden;
    		flex-shrink: 0;
    		`}>
    		<img className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		max-width: 100%;
    		overflow: hidden;
    		max-height: 100%;
    		object-fit: cover;
    		`} alt="" />
            </div>
    		<b className={css`position: absolute;
    		top: 954px;
    		left: 292px;
    		font-size: var(--fs-24);
    		text-decoration: underline;
    		text-align: center;
    		flex-shrink: 0;
    		`}>Commits Included</b>
    		<div className={css`position: absolute;
    		top: 1029px;
    		left: 292px;
    		border-radius: var(--br-5);
    		background-color: var(--color-gainsboro);
    		border: var(--border-1);
    		box-sizing: border-box;
    		width: var(--width-22);
    		height: var(--height-22);
    		opacity: var(--opacity-0_8);
    		flex-shrink: 0;
    		`} />
    		<div className={css`position: absolute;
    		top: 1191px;
    		left: 321px;
    		font-weight: 500;
    		display: inline-block;
    		width: 336px;
    		height: var(--height-19);
    		flex-shrink: 0;
    		`}>Add responsive navigation menu (0b6c4e8)</div>
    		<div className={css`position: absolute;
    		top: 1189px;
    		left: 292px;
    		width: var(--width-22);
    		height: var(--height-22);
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-5);
    		background-color: var(--color-gainsboro);
    		border: var(--border-1);
    		box-sizing: border-box;
    		opacity: var(--opacity-0_8);
    		`} />
    		<div className={css`position: absolute;
    		top: 13.64%;
    		left: 13.64%;
    		font-weight: 500;
    		`}>✔</div>
            </div>
    		<div className={css`position: absolute;
    		top: 1063px;
    		left: 321px;
    		font-weight: 500;
    		display: inline-block;
    		width: 316px;
    		height: var(--height-19);
    		flex-shrink: 0;
    		`}>Improve keyboard focus styles (c84a1b9)</div>
    		<div className={css`position: absolute;
    		top: 1157px;
    		left: 292px;
    		width: var(--width-22);
    		height: var(--height-22);
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-5);
    		background-color: var(--color-gainsboro);
    		border: var(--border-1);
    		box-sizing: border-box;
    		opacity: var(--opacity-0_8);
    		`} />
    		<div className={css`position: absolute;
    		top: 13.64%;
    		left: 13.64%;
    		font-weight: 500;
    		`}>✔</div>
            </div>
    		<div className={css`position: absolute;
    		top: 1127px;
    		left: 321px;
    		font-weight: 500;
    		display: inline-block;
    		width: 298px;
    		height: var(--height-19);
    		flex-shrink: 0;
    		`}>Update project descriptions (e73b0c6)</div>
    		<div className={css`position: absolute;
    		top: 1125px;
    		left: 292px;
    		width: var(--width-22);
    		height: var(--height-22);
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-5);
    		background-color: var(--color-gainsboro);
    		border: var(--border-1);
    		box-sizing: border-box;
    		opacity: var(--opacity-0_8);
    		`} />
    		<div className={css`position: absolute;
    		top: 13.64%;
    		left: 13.64%;
    		font-weight: 500;
    		`}>✔</div>
            </div>
    		<div className={css`position: absolute;
    		top: 1095px;
    		left: 321px;
    		font-weight: 500;
    		display: inline-block;
    		width: 269px;
    		height: var(--height-19);
    		flex-shrink: 0;
    		`}>Add social links to footer (d19e5f2)</div>
    		<div className={css`position: absolute;
    		top: 1093px;
    		left: 292px;
    		width: var(--width-22);
    		height: var(--height-22);
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-5);
    		background-color: var(--color-gainsboro);
    		border: var(--border-1);
    		box-sizing: border-box;
    		opacity: var(--opacity-0_8);
    		`} />
    		<div className={css`position: absolute;
    		top: 13.64%;
    		left: 13.64%;
    		font-weight: 500;
    		`}>✔</div>
            </div>
    		<div className={css`position: absolute;
    		top: 1159px;
    		left: 321px;
    		font-weight: 500;
    		display: inline-block;
    		width: 292px;
    		height: var(--height-19);
    		flex-shrink: 0;
    		`}>Optimize homepage images (f5a28d1)</div>
    		<div className={css`position: absolute;
    		top: 1061px;
    		left: 292px;
    		width: var(--width-22);
    		height: var(--height-22);
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-5);
    		background-color: var(--color-gainsboro);
    		border: var(--border-1);
    		box-sizing: border-box;
    		opacity: var(--opacity-0_8);
    		`} />
    		<div className={css`position: absolute;
    		top: 13.64%;
    		left: 13.64%;
    		font-weight: 500;
    		`}>✔</div>
            </div>
    		<div className={css`position: absolute;
    		top: 1031px;
    		left: 321px;
    		font-weight: 500;
    		display: inline-block;
    		width: 357px;
    		height: var(--height-19);
    		flex-shrink: 0;
    		`}>Add contact form success message (b2f6d83)</div>
    		<div className={css`position: absolute;
    		top: 1029px;
    		left: 292px;
    		width: var(--width-22);
    		height: var(--height-22);
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-5);
    		background-color: var(--color-gainsboro);
    		border: var(--border-1);
    		box-sizing: border-box;
    		opacity: var(--opacity-0_8);
    		`} />
    		<div className={css`position: absolute;
    		top: 13.64%;
    		left: 13.64%;
    		font-weight: 500;
    		`}>✔</div>
            </div>
    		<div className={css`position: absolute;
    		top: 999px;
    		left: 321px;
    		font-weight: 500;
    		display: inline-block;
    		width: 247px;
    		height: var(--height-19);
    		flex-shrink: 0;
    		`}>Polish mobile spacing (a7c91e4)</div>
    		<div className={css`position: absolute;
    		top: 997px;
    		left: 292px;
    		width: var(--width-22);
    		height: var(--height-22);
    		flex-shrink: 0;
    		`}>
    		<div className={css`position: absolute;
    		height: 100%;
    		width: 100%;
    		top: 0%;
    		right: 0%;
    		bottom: 0%;
    		left: 0%;
    		border-radius: var(--br-5);
    		background-color: var(--color-gainsboro);
    		border: var(--border-1);
    		box-sizing: border-box;
    		opacity: var(--opacity-0_8);
    		`} />
    		<div className={css`position: absolute;
    		top: 13.64%;
    		left: 13.64%;
    		font-weight: 500;
    		`}>✔</div>
            </div>
        </div>);
};

export default NewProjectSetup ;
