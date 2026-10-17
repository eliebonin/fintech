import {StrategyPageContent} from '../strategy-page-content';
export const dynamic='force-dynamic';
export default async function CreateStrategyPage(){return StrategyPageContent({createOnly:true});}
