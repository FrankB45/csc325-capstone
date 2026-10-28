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
--color-firebrick: #ba0202;
--color-gray-300: rgba(11, 37, 69, 0.5);
--color-gainsboro: #d9d9d9;


/* Padding */
--padding-0: 0px;
--br-5: 5px;
--padding-12: 12px;

/* BorderRadius */
--br-10: 10px;

/* Font */
--font-inter: Inter, Arial, sans-serif;
--font-jetbrains-mono: JetBrains Mono, Arial, sans-serif;

/* FontSize */
--fs-16: 16px;
--fs-20: 20px;
--fs-24: 24px;
--fs-32: 32px;
--fs-36: 36px;

/* Gradients */
--gradient-1: #d9d9d9 padding-box, linear-gradient(98.52deg, #f7b32b, var(--color-coral-100)) border-box;

/* WidthHeights */
--height-19: 19px;
--height-22: 22px;
--height-24: 24px;
--width-22: 22px;
--height-64: 64px;
--height-459: 459px;

/* LineHeights */
--lh-20: 20px;
--lh-48: 48px;

/* Opacities */
--opacity-0_8: 0.8;


--left-292: 292px;
--left-321: 321px;
--left-0: 0px;
--left-50: 50px;
--top-0: 0px;
--top-2: 2px;

}
    
    
`;
        }