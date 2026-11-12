import {z} from 'zod';
const status=z.enum(['passed','failed','running','error','skipped','not_run','environment_error','missing_input']);
const text=z.string().max(20000);
const metric=z.number().int().nonnegative();
export const reportSchema=z.object({schemaVersion:z.literal('1.0'),analyses:z.array(z.object({
 id:z.string().min(1),repository:text,prNumber:z.number().int().positive(),prTitle:text,headSha:text,runId:z.number().int().nonnegative(),
 analyzedAt:z.string().datetime(),githubUrl:z.string().url().refine(s=>/^https:\/\/github\.com\/[^/]+\/[^/]+\/pull\/\d+$/.test(s),'GitHub PR URL required').nullable(),
 status:z.enum(['passed','failed','running','partial']),checks:z.object({ruffStatus:status,pytestStatus:status,errorSummary:text.nullable()}),
 review:z.object({status,summary:text,findings:z.array(z.object({file:text,line:z.number().int().positive(),evidence:text,suggestion:text,locationVerified:z.boolean(),adjudication:z.enum(['unreviewed','confirmed','false_positive'])}))}),
 tests:z.array(z.object({target:text,code:text,purpose:text,executionStatus:status,failureReason:text.nullable()})),
 discordRequestStatus:z.enum(['passed','error','not_configured']),duration:z.number().nonnegative().nullable(),execution:z.array(z.object({name:text,status:text}))
})).max(1000),evaluation:z.object({cases:metric,bug_review_cases:metric,fixed_false_positives_code_inspected:metric,valid_locations:metric,published_locations:metric,fixed_execution_without_environment_error:metric,fixed_passed_tests:metric,total_same_draft_tests:metric,cases_with_detecting_test:metric,same_draft_test_outcomes:z.record(metric)}).nullable()}).superRefine((v,c)=>{if(new Set(v.analyses.map(a=>a.id)).size!==v.analyses.length)c.addIssue({code:'custom',message:'重複したID / 중복 ID'});});
export type Report=z.infer<typeof reportSchema>;
export type Analysis=Report['analyses'][number];
export function parseReport(raw:unknown){return reportSchema.parse(raw)}
export function codeUrl(a:Analysis,file:string,line:number){
 if(!a.githubUrl||! /^[0-9a-f]{40}$/.test(a.headSha)||file.split('/').some(p=>p==='..'||p==='.')||file.startsWith('/'))return null;
 return `https://github.com/${a.repository}/blob/${a.headSha}/${file.split('/').map(encodeURIComponent).join('/')}#L${line}`;
}
