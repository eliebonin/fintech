import {createTheme} from '@mui/material';
import {workspacePresentation as presentation} from './workspace-presentation';

export const workspaceTheme=createTheme({
 palette:{mode:'light',primary:{main:presentation.primary},secondary:{main:'#e9a23b'},background:{default:presentation.background,paper:'#ffffff'},text:{primary:presentation.ink,secondary:'#667085'}},
 typography:{fontFamily:'var(--font-inter), Arial, sans-serif',h4:{fontWeight:750,letterSpacing:'-0.03em'},h5:{fontWeight:700,letterSpacing:'-0.02em'},h6:{fontWeight:700},button:{textTransform:'none',fontWeight:650}},
 shape:{borderRadius:12},
 components:{
  MuiCard:{styleOverrides:{root:{boxShadow:'0 6px 24px rgba(24, 39, 75, 0.06)',border:'1px solid #e7ecf4'}}},
  MuiButton:{defaultProps:{disableElevation:true},styleOverrides:{root:{borderRadius:presentation.controlRadius,minHeight:presentation.actionHeight},sizeSmall:{minHeight:presentation.compactActionHeight}}},
  MuiTableCell:{styleOverrides:{root:{borderColor:'#edf0f5'}}},
 },
});
