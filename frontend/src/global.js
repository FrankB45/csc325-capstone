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
--color-gray-400: #767875;
--color-indigo: #3b0086;
--color-slategray: #8e6c88;
--color-lightgray: #cfd2cd;
--color-firebrick: #ba0202;
--color-gray-300: rgba(11, 37, 69, 0.5);
--color-gainsboro: #d9d9d9;
--color-gray-400: rgba(255, 255, 255, 0.4);
--color-gray-500: rgba(255, 255, 255, 0.1);
--color-slategray-200: rgba(142, 108, 136, 0.8);
--color-black: #000;


/* Gap */
--gap-8: 8px;


/* Padding */
--padding-0: 0px;
--padding-2: 2px;
--br-5: 5px;
--padding-6: 6px;
--padding-8: 8px;
--padding-10: 10px;
--padding-12: 12px;
--padding-16: 16px;
--padding-20: 20px;
--padding-24: 24px;
--padding-48: 48px;

/* BorderRadius */
--br-10: 10px;
--br-12: 12px;
--br-16: 16px;
--br-50: 50%;

/* Font */
--font-inter: Inter, Arial, sans-serif;
--font-jetbrains-mono: JetBrains Mono, Arial, sans-serif;
--font-dm-mono: DM Mono, Arial, sans-serif;
--font-dm-sans: DM Sans, Arial, sans-serif;

/* FontSize */
--fs-12: 12px;
--fs-14: 14px;
--fs-16: 16px;
--fs-20: 20px;
--fs-24: 24px;
--fs-32: 32px;
--fs-36: 36px;

/* Borders */
--border-1: 1px solid var(--color-lightgray);

/* Gradients */
--gradient-1: #d9d9d9 padding-box, linear-gradient(98.52deg, #f7b32b, var(--color-coral-100)) border-box;
--gradient-2: linear-gradient(122.33deg, #f7b32b, var(--color-coral)) border-box;
--gradient-3: linear-gradient(90deg, #f7b32b, var(--color-coral));



/* WidthHeights */
--height-14: 14px;
--height-19: 19px;
--height-22: 22px;
--height-24: 24px;
--height-26: 26px;
--height-32: 32px;
--width-22: 22px;
--height-35: 35px;
--width-35: 35px;
--height-64: 64px;
--height-459: 459px;
--width-14: 14px;
--width-676: 676px;
--width-678: 678px;

/* LineHeights */
--lh-16: 16px;
--lh-20: 20px;
--lh-24: 24px;
--lh-28: 28px;
--lh-22_75: 22.75px;
--lh-48: 48px;

/* Opacities */
--opacity-0_8: 0.8;


--left-40: 40px;
--left-292: 292px;
--left-321: 321px;
--left-0: 0px;
--left-50: 50px;
--top-0: 0px;
--top-2: 2px;
--top-805: 805px;
--top-858: 858px;

}
    
    
`;
        }