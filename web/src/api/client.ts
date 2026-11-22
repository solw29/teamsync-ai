import {z} from 'zod';
import {reportSchema} from '../schema';
export const analysisSchema=reportSchema.innerType().shape.analyses.element;
export const repositoriesSchema=z.object({items:z.array(z.object({id:z.string(),externalId:z.number().int().positive(),fullName:z.string(),workflowIds:z.array(z.number().int().positive())}))});
export const listSchema=z.object({items:z.array(analysisSchema),nextCursor:z.string().nullable(),source:z.literal('api'),lastSyncedAt:z.string().nullable(),syncError:z.string().nullable().optional()});
export const statsSchema=z.object({counts:z.record(z.number().int().nonnegative()),total:z.number().int().nonnegative(),asOf:z.string(),days:z.number(),version:z.number(),cacheSource:z.enum(['hit','miss','database_fallback'])});
export const sessionSchema=z.object({username:z.string(),csrfToken:z.string()});
export const detailSchema=z.object({analysis:analysisSchema,schemaVersion:z.string(),runAttempt:z.number().nullable(),githubStatus:z.string(),githubConclusion:z.string().nullable(),collectionStatus:z.string(),collectedAt:z.string()});
export const jobSchema=z.object({id:z.string(),status:z.enum(['queued','running','retrying','succeeded','failed','cancelled']),attempts:z.number(),reason:z.string().nullable(),runId:z.number(),runAttempt:z.number(),createdAt:z.string(),updatedAt:z.string(),nextRetryAt:z.string().nullable(),finishedAt:z.string().nullable(),events:z.array(z.object({status:z.string(),reason:z.string().nullable(),at:z.string()})).optional()});
export class ApiError extends Error{constructor(public code:string,public status:number){super(code)}}
export class ApiClient{
 constructor(public base='/api',private csrf='',private expired:()=>void=()=>{}){}
 async request<T>(path:string,schema:z.ZodType<T>,options:RequestInit={}){
  const response=await fetch(this.base+path,{...options,credentials:'include',headers:{'Content-Type':'application/json',...(this.csrf?{'X-CSRF-Token':this.csrf}:{}),...options.headers}});
  if(!response.ok){let code='server_unavailable';try{code=(await response.json()).error?.code||code}catch{/*No response body or credential logs.*/}if(response.status===401)this.expired();throw new ApiError(code,response.status)}
  return schema.parse(await response.json());
 }
}
export const message=(error:unknown)=>{
 const code=error instanceof ApiError?error.code:'connection_unavailable';
 return ({authentication_required:'로그인이 필요하거나 세션이 만료되었습니다.',csrf_required:'보안 토큰이 만료되었습니다. 다시 로그인하세요.',github_credential_missing:'결과 수집용 GitHub 연결이 필요합니다.',github_permission_denied:'선택 저장소의 GitHub 읽기 권한을 확인하세요.',artifact_unavailable:'실행 보고서를 찾지 못했습니다.',database_unavailable:'서버 저장소에 연결할 수 없습니다.',invalid_credentials:'계정 정보를 확인하세요.',connection_unavailable:'서버에 연결하지 못했습니다.',repository_not_found:'허용된 저장소를 찾지 못했습니다.'} as Record<string,string>)[code]||`요청을 처리하지 못했습니다 (${code}).`;
};
