import { useCallback } from 'react';
import {css} from "@emotion/css";
import {useNavigate} from "react-router-dom";



const Info = () => {
  	const navigate = useNavigate();
  	
  	const onInfoIconClick = useCallback(() => {
    		navigate("/");
  	}, [navigate]);
  	
  	
  	const onGitGalleryLogoContainerClick = useCallback(() => {
    		// Add your code here
  	}, []);
  	
  	return (
    		<div className={css`width: 100%;
height: 2370px;
position: relative;
background-color: var(--color-gray-100);
overflow: hidden;
text-align: left;
font-size: var(--fs-20);
color: var(--color-gray-200);
font-family: var(--font-dm-sans);
`}>
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
    		<div className={css`position: absolute;
    		top: 176px;
    		left: 40px;
    		width: 720px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: 40px var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		flex-shrink: 0;
    		font-size: 30px;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		align-items: center;
    		`}>
    		<div className={css`display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<b className={css`position: relative;
    		line-height: 36px;
    		`}>About Git Gallery</b>
                    </div>
                </div>
    		<div className={css`align-self: stretch;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-12) var(--padding-0) var(--padding-0);
    		font-size: var(--fs-16);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`width: 720px;
    		position: relative;
    		line-height: 26px;
    		display: inline-block;
    		`}>Git Gallery turns a developer tool — version control — into a visual story anyone can follow. Below you'll find answers to common questions, and an AI assistant ready to help.</div>
                </div>
            </div>
    		<div className={css`position: absolute;
    		top: 290px;
    		left: 40px;
    		width: 1360px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-48) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		flex-shrink: 0;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<b className={css`position: relative;
    		line-height: var(--lh-28);
    		`}>How it works</b>
                </div>
    		<div className={css`align-self: stretch;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-24) var(--padding-0) var(--padding-0);
    		font-size: var(--fs-12);
    		`}>
    		<div className={css`width: 1360px;
    		height: 187px;
    		display: grid;
    		box-sizing: border-box;
    		grid-template-columns: 427px 1fr 1fr;
    		grid-template-rows: repeat(2, 187px);
    		gap: 16px;
    		`}>
    		<div className={css`width: 426px;
    		border-radius: var(--br-16);
    		background: var(--gradient-3);
    		border: 5px solid transparent;
    		box-sizing: border-box;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-20);
    		grid-column: 1;
    		grid-row: 2 / span 41;
    		height: 187px;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		font-family: var(--font-dm-mono);
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-16);
    		font-weight: 500;
    		background: var(--gradient-3);
    		-webkit-background-clip: text;
    		-webkit-text-fill-color: transparent;
    		`}>01</div>
                            </div>
    		<div className={css`width: 189.3px;
    		height: var(--height-32);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-8) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		font-size: var(--fs-16);
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-24);
    		font-weight: 600;
    		`}>Paste a repo link</div>
                            </div>
    		<div className={css`width: 339px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-8) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`width: 339px;
    		position: relative;
    		line-height: var(--lh-22_75);
    		display: inline-block;
    		`}>Submit a public GitHub URL for a static HTML/CSS/JS site.</div>
                            </div>
                        </div>
    		<div className={css`width: 437px;
    		border-radius: var(--br-16);
    		background: var(--gradient-3);
    		border: 5px solid transparent;
    		box-sizing: border-box;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-20) 21px var(--padding-20) var(--padding-20);
    		grid-column: 3;
    		grid-row: 1 / span 43;
    		height: 197px;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		font-family: var(--font-dm-mono);
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-16);
    		font-weight: 500;
    		background: var(--gradient-3);
    		-webkit-background-clip: text;
    		-webkit-text-fill-color: transparent;
    		`}>03</div>
                            </div>
    		<div className={css`width: 189.3px;
    		height: var(--height-32);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-8) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		font-size: var(--fs-16);
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-24);
    		font-weight: 600;
    		`}>Browse the timeline</div>
                            </div>
    		<div className={css`width: 189.3px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-8) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`width: 368px;
    		position: relative;
    		line-height: var(--lh-22_75);
    		display: inline-block;
    		flex-shrink: 0;
    		`}>Tap any dot to see a screenshot of the site at that commit. Compare any two snapshots side by side.</div>
                            </div>
                        </div>
    		<div className={css`width: 427px;
    		border-radius: var(--br-16);
    		background: var(--gradient-3);
    		border: 5px solid transparent;
    		box-sizing: border-box;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-20);
    		grid-column: 2;
    		grid-row: 2 / span 41;
    		height: 187px;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		font-family: var(--font-dm-mono);
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-16);
    		font-weight: 500;
    		background: var(--gradient-3);
    		-webkit-background-clip: text;
    		-webkit-text-fill-color: transparent;
    		`}>02</div>
                            </div>
    		<div className={css`width: 189.3px;
    		height: var(--height-32);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-8) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		font-size: var(--fs-16);
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-24);
    		font-weight: 600;
    		`}>AI selects commits</div>
                            </div>
    		<div className={css`width: 326px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-8) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`align-self: stretch;
    		position: relative;
    		line-height: var(--lh-22_75);
    		`}>The AI groups commits into milestones and picks the most visually significant ones.</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
    		<div className={css`position: absolute;
    		top: 577px;
    		left: 40px;
    		width: 1360px;
    		height: 1101px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-48) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		flex-shrink: 0;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<b className={css`position: relative;
    		line-height: var(--lh-28);
    		`}>Frequently Asked Questions</b>
                </div>
    		<div className={css`align-self: stretch;
    		height: 833px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-24) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		gap: 9px;
    		font-size: var(--fs-16);
    		`}>
    		<div className={css`align-self: stretch;
    		height: 163px;
    		border-radius: var(--br-12);
    		border: var(--border-1);
    		box-sizing: border-box;
    		overflow: hidden;
    		flex-shrink: 0;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		align-items: center;
    		justify-content: space-between;
    		padding: var(--padding-16) var(--padding-20);
    		`}>
    		<div className={css`display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-24);
    		font-weight: 500;
    		`}>What is Git Gallery?</div>
                            </div>
                        </div>
    		<div className={css`align-self: stretch;
    		border-top: var(--border-1);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-16) var(--padding-20) var(--padding-20);
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`width: var(--width-678);
    		position: relative;
    		line-height: var(--lh-22_75);
    		display: inline-block;
    		`}>Git Gallery is a visual version control explorer designed for non-technical stakeholders. Instead of reading code diffs, you browse screenshots of your website at every commit — so designers, managers, and clients can follow a project's evolution without any Git knowledge.</div>
                        </div>
                    </div>
    		<div className={css`align-self: stretch;
    		height: 163.3px;
    		border-radius: var(--br-12);
    		border: var(--border-1);
    		box-sizing: border-box;
    		overflow: hidden;
    		flex-shrink: 0;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		align-items: center;
    		justify-content: space-between;
    		padding: var(--padding-16) var(--padding-20);
    		`}>
    		<div className={css`display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-24);
    		font-weight: 500;
    		`}>What kind of repositories does Git Gallery support?</div>
                            </div>
                        </div>
    		<div className={css`align-self: stretch;
    		border-top: var(--border-1);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-16) var(--padding-20) var(--padding-20);
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`width: var(--width-678);
    		position: relative;
    		line-height: var(--lh-22_75);
    		display: inline-block;
    		`}>Git Gallery works with public GitHub repositories that contain a simple HTML, CSS, and JavaScript website. The repo must have an index.html at the root and no server-side rendering — it needs to run as a static site so we can screenshot it reliably.</div>
                        </div>
                    </div>
    		<div className={css`align-self: stretch;
    		height: 163.3px;
    		border-radius: var(--br-12);
    		border: var(--border-1);
    		box-sizing: border-box;
    		overflow: hidden;
    		flex-shrink: 0;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		align-items: center;
    		justify-content: space-between;
    		padding: var(--padding-16) var(--padding-20);
    		`}>
    		<div className={css`display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-24);
    		font-weight: 500;
    		`}>How does the AI assistant work?</div>
                            </div>
                        </div>
    		<div className={css`align-self: stretch;
    		border-top: var(--border-1);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-16) var(--padding-20) var(--padding-20);
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`width: var(--width-678);
    		position: relative;
    		line-height: var(--lh-22_75);
    		display: inline-block;
    		`}>The AI reviews commit messages and code changes to group consecutive commits into thematic milestones (e.g. "Foundation", "Content", "Polish"). When you select two commits to compare, it describes the visible differences in plain language — no code reading required.</div>
                        </div>
                    </div>
    		<div className={css`align-self: stretch;
    		height: 140.5px;
    		border-radius: var(--br-12);
    		border: var(--border-1);
    		box-sizing: border-box;
    		overflow: hidden;
    		flex-shrink: 0;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		align-items: center;
    		justify-content: space-between;
    		padding: var(--padding-16) var(--padding-20);
    		`}>
    		<div className={css`display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-24);
    		font-weight: 500;
    		`}>Can I use private repositories?</div>
                            </div>
                        </div>
    		<div className={css`align-self: stretch;
    		border-top: var(--border-1);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-16) var(--padding-20) var(--padding-20);
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`width: var(--width-678);
    		position: relative;
    		line-height: var(--lh-22_75);
    		display: inline-block;
    		`}>Not yet. Git Gallery currently requires a publicly accessible repository so it can fetch and render the site for screenshots. Support for private repos with a personal access token is on our roadmap.</div>
                        </div>
                    </div>
    		<div className={css`align-self: stretch;
    		height: 163.3px;
    		border-radius: var(--br-12);
    		border: var(--border-1);
    		box-sizing: border-box;
    		overflow: hidden;
    		flex-shrink: 0;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		align-items: center;
    		justify-content: space-between;
    		padding: var(--padding-16) var(--padding-20);
    		`}>
    		<div className={css`display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-24);
    		font-weight: 500;
    		`}>How many commits can a project have?</div>
                            </div>
                        </div>
    		<div className={css`align-self: stretch;
    		border-top: var(--border-1);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-16) var(--padding-20) var(--padding-20);
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`width: var(--width-678);
    		position: relative;
    		line-height: var(--lh-22_75);
    		display: inline-block;
    		`}>There is no hard limit, but for best performance we recommend repositories with fewer than 200 commits. Very large histories are summarised — the AI picks the most visually significant commits so the timeline stays navigable.</div>
                        </div>
                    </div>
    		<div className={css`align-self: stretch;
    		height: 163.3px;
    		border-radius: var(--br-12);
    		border: var(--border-1);
    		box-sizing: border-box;
    		overflow: hidden;
    		flex-shrink: 0;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		align-items: center;
    		justify-content: space-between;
    		padding: var(--padding-16) var(--padding-20);
    		`}>
    		<div className={css`display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-24);
    		font-weight: 500;
    		`}>Is my repository data stored anywhere?</div>
                            </div>
                        </div>
    		<div className={css`align-self: stretch;
    		border-top: var(--border-1);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-16) var(--padding-20) var(--padding-20);
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`width: var(--width-678);
    		position: relative;
    		line-height: var(--lh-22_75);
    		display: inline-block;
    		`}>Git Gallery only reads publicly available data from GitHub. Screenshots are generated on-demand and cached temporarily. We do not store your source code or commit history on our servers beyond the current session.</div>
                        </div>
                    </div>
                </div>
            </div>
    		<div className={css`position: absolute;
    		top: 1678px;
    		left: 40px;
    		width: 1359px;
    		height: 894px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: 56px var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		flex-shrink: 0;
    		font-size: var(--fs-14);
    		color: var(--color-slategray);
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		font-size: var(--fs-20);
    		color: var(--color-gray-200);
    		`}>
    		<b className={css`position: relative;
    		line-height: var(--lh-28);
    		`}>Ask the AI Assistant</b>
                </div>
    		<div className={css`width: 720px;
    		height: 28px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-8) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-20);
    		`}>Can't find your answer above? Ask the assistant anything about Git Gallery.</div>
                </div>
    		<div className={css`align-self: stretch;
    		height: 334px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-20) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		color: var(--color-gray-100);
    		`}>
    		<div className={css`align-self: stretch;
    		height: 302px;
    		border-radius: var(--br-16);
    		background-color: var(--color-slategray);
    		overflow: hidden;
    		flex-shrink: 0;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`align-self: stretch;
    		border-bottom: 1px solid var(--color-gray-600);
    		display: flex;
    		align-items: center;
    		padding: 14px var(--padding-20);
    		gap: 10px;
    		`}>
    		<div className={css`height: 8px;
    		width: 8px;
    		position: relative;
    		border-radius: 16777200px;
    		background-color: var(--color-coral-100);
    		opacity: 0.98;
    		`} />
    		<div className={css`display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-20);
    		font-weight: 600;
    		`}>Git Gallery Assistant</div>
                            </div>
    		<div className={css`flex: 1;
    		display: flex;
    		align-items: flex-start;
    		justify-content: flex-end;
    		font-size: var(--fs-12);
    		color: var(--color-gray-500);
    		font-family: var(--font-dm-mono);
    		`}>
    		<div className={css`display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-16);
    		`}>AI</div>
                                </div>
                            </div>
                        </div>
    		<div className={css`align-self: stretch;
    		height: 160px;
    		overflow: hidden;
    		flex-shrink: 0;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-16) var(--padding-20);
    		box-sizing: border-box;
    		min-height: 160px;
    		max-height: 300px;
    		`}>
    		<div className={css`align-self: stretch;
    		height: 65.5px;
    		display: flex;
    		align-items: flex-start;
    		`}>
    		<div className={css`align-self: stretch;
    		border-radius: var(--br-12) var(--br-12) var(--br-12) 4px;
    		background-color: var(--color-gray-600);
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-10) var(--padding-16);
    		`}>
    		<div className={css`width: 512px;
    		position: relative;
    		line-height: var(--lh-22_75);
    		display: inline-block;
    		`}>Hi! I'm the Git Gallery assistant. Ask me anything about how the app works, what repos are supported, or how to get started.</div>
                                </div>
                            </div>
                        </div>
    		<div className={css`align-self: stretch;
    		height: 93px;
    		border-top: 1px solid var(--color-gray-600);
    		box-sizing: border-box;
    		display: flex;
    		align-items: flex-start;
    		padding: var(--padding-16) var(--padding-0) var(--padding-16) var(--padding-20);
    		gap: 34px;
    		color: var(--color-gray-300);
    		`}>
    		<div className={css`height: var(--height-64);
    		width: 998px;
    		border-radius: var(--br-12);
    		background-color: var(--color-gainsboro);
    		overflow: hidden;
    		flex-shrink: 0;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		justify-content: center;
    		padding: var(--padding-10) var(--padding-16);
    		box-sizing: border-box;
    		`}>
    		<div className={css`align-self: stretch;
    		position: relative;
    		`}>Ask something about Git Gallery…</div>
                            </div>
    		<div className={css`height: var(--height-64);
    		width: 272px;
    		border-radius: 10px;
    		background-color: var(--color-coral-100);
    		display: flex;
    		flex-direction: column;
    		align-items: center;
    		justify-content: center;
    		padding: var(--padding-10) var(--padding-16);
    		box-sizing: border-box;
    		opacity: 0.4;
    		flex-shrink: 0;
    		text-align: center;
    		font-size: 36px;
    		color: var(--color-gray-100);
    		font-family: var(--font-inter);
    		`}>
    		<b className={css`position: relative;
    		line-height: var(--lh-20);
    		`}>Send</b>
                            </div>
                        </div>
                    </div>
                </div>
    		<div className={css`align-self: stretch;
    		height: 393px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: 32px var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		`}>
    		<div className={css`width: 1369px;
    		max-width: 1369px;
    		height: 371px;
    		border-radius: var(--br-12);
    		background: var(--gradient-3);
    		border: 5px solid transparent;
    		box-sizing: border-box;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-20);
    		`}>
    		<div className={css`align-self: stretch;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		`}>
    		<div className={css`position: relative;
    		line-height: var(--lh-20);
    		font-weight: 600;
    		`}>Repository requirements</div>
                        </div>
    		<div className={css`width: var(--width-676);
    		height: 136px;
    		display: flex;
    		flex-direction: column;
    		align-items: flex-start;
    		padding: var(--padding-12) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		color: var(--color-slategray-200);
    		`}>
    		<div className={css`align-self: stretch;
    		height: 20px;
    		display: flex;
    		align-items: flex-start;
    		gap: var(--gap-8);
    		`}>
    		<div className={css`display: flex;
    		align-items: flex-start;
    		padding: var(--padding-2) var(--padding-0) var(--padding-0);
    		`}>
    		<img className={css`height: var(--height-14);
    		width: var(--width-14);
    		position: relative;
    		`} alt="" />
                                </div>
    		<div className={css`position: relative;
    		line-height: var(--lh-20);
    		`}>Public GitHub repository</div>
                            </div>
    		<div className={css`width: var(--width-676);
    		height: var(--height-26);
    		display: flex;
    		align-items: flex-start;
    		padding: var(--padding-6) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		gap: var(--gap-8);
    		`}>
    		<div className={css`display: flex;
    		align-items: flex-start;
    		padding: var(--padding-2) var(--padding-0) var(--padding-0);
    		`}>
    		<img className={css`height: var(--height-14);
    		width: var(--width-14);
    		position: relative;
    		`} alt="" />
                                </div>
    		<div className={css`position: relative;
    		line-height: var(--lh-20);
    		`}>Static site: HTML, CSS, JavaScript only</div>
                            </div>
    		<div className={css`width: var(--width-676);
    		height: var(--height-26);
    		display: flex;
    		align-items: flex-start;
    		padding: var(--padding-6) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		gap: var(--gap-8);
    		`}>
    		<div className={css`display: flex;
    		align-items: flex-start;
    		padding: var(--padding-2) var(--padding-0) var(--padding-0);
    		`}>
    		<img className={css`height: var(--height-14);
    		width: var(--width-14);
    		position: relative;
    		`} alt="" />
                                </div>
    		<div className={css`position: relative;
    		line-height: var(--lh-20);
    		`}>index.html at the repository root</div>
                            </div>
    		<div className={css`width: var(--width-676);
    		height: var(--height-26);
    		display: flex;
    		align-items: flex-start;
    		padding: var(--padding-6) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		gap: var(--gap-8);
    		`}>
    		<div className={css`display: flex;
    		align-items: flex-start;
    		padding: var(--padding-2) var(--padding-0) var(--padding-0);
    		`}>
    		<img className={css`height: var(--height-14);
    		width: var(--width-14);
    		position: relative;
    		`} alt="" />
                                </div>
    		<div className={css`position: relative;
    		line-height: var(--lh-20);
    		`}>No server-side rendering or build step required</div>
                            </div>
    		<div className={css`width: var(--width-676);
    		height: var(--height-26);
    		display: flex;
    		align-items: flex-start;
    		padding: var(--padding-6) var(--padding-0) var(--padding-0);
    		box-sizing: border-box;
    		gap: var(--gap-8);
    		`}>
    		<div className={css`display: flex;
    		align-items: flex-start;
    		padding: var(--padding-2) var(--padding-0) var(--padding-0);
    		`}>
    		<img className={css`height: var(--height-14);
    		width: var(--width-14);
    		position: relative;
    		`} alt="" />
                                </div>
    		<div className={css`position: relative;
    		line-height: var(--lh-20);
    		`}>No external assets loaded from authenticated sources</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>);
};

export default Info ;
