import {ruleDescription,ruleLabel} from './model';
import styles from './profiles.module.css';

/** Explanations stay visible alongside the rules, including in the published view. */
export function LifecycleRuleHelp(){
 return <section className={styles.ruleHelp} aria-label="Lifecycle treatment guide"><h4>How lifecycle choices differ</h4><dl>{['INPUT','INHERIT','ALLOCATION'].map(value=><div key={value}><dt>{ruleLabel(value)}</dt><dd>{ruleDescription(value)}</dd></div>)}</dl></section>;
}
