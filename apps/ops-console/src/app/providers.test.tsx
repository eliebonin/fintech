import {expect,it} from 'vitest';
import {Providers} from './providers';

it('aligns default MUI action dimensions with native workspace actions',()=>{
 // AppRouterCacheProvider collects SSR CSS for Next's stream, not static HTML.
 // Real computed CSS is checked by the isolated browser acceptance case.
 const theme=Providers({children:null}).props.children.props.theme;
 expect(theme.components.MuiButton.styleOverrides.root).toEqual({minHeight:40,borderRadius:8});
 expect(theme.components.MuiButton.styleOverrides.sizeSmall).toEqual({minHeight:32});
});
