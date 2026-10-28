import { injectGlobal } from "@emotion/css";

export default function createGlobalStyle() {
  	injectGlobal`
        
body {
    margin: 0; line-height: normal;
}
:root {

/* Common Style Variables */

/* Color */
--color-coral-100: #ff7f51;
--color-coral-200: #e57a44;
--color-gray-100: #fefeff;
--color-gray-200: #0b2545;
--color-indigo: #3b0086;
--color-slategray: #8e6c88;
--color-lightgray: #cfd2cd;

/* Padding */
--padding-0: 0px;
--padding-12: 12px;

/* BorderRadius */
--br-10: 10px;

/* Font */
--font-inter: Inter, Arial, sans-serif;
--font-jetbrains-mono: JetBrains Mono, Arial, sans-serif;

/* FontSize */
--fs-16: 16px;
--fs-24: 24px;
--fs-36: 36px;

/* Gradients */
--gradient-1: #d9d9d9 padding-box, linear-gradient(98.52deg, #f7b32b, var(--color-coral-100)) border-box;

/* WidthHeights */
--height-64: 64px;
--height-459: 459px;

/* LineHeights */
--lh-20: 20px;
--lh-48: 48px;

}
    
    
`;
        }