import type {Report} from '../schema';
export interface DataSource{kind:'demo'|'import'|'api';load(signal?:AbortSignal):Promise<Report>}
export class JsonSource implements DataSource{
 constructor(public kind:'demo'|'import',private reader:(signal?:AbortSignal)=>Promise<Report>){}
 load(signal?:AbortSignal){return this.reader(signal)}
}

export class ApiSource implements DataSource{
 readonly kind='api' as const;
 constructor(private reader:(signal?:AbortSignal)=>Promise<Report>){}
 load(signal?:AbortSignal){return this.reader(signal)}
}
// Only the non-secret source preference survives a refresh. No result, cookie,
// password, CSRF token or GitHub credential is stored in browser storage.
export function initialApiMode(configured:boolean){try{const mode=sessionStorage.getItem('teamsync.source');return mode==='api'||(mode!=='file'&&configured)}catch{return configured}}
export function rememberSource(mode:'api'|'file'){try{sessionStorage.setItem('teamsync.source',mode)}catch{/* Storage-disabled browsers retain only in-memory choice. */}}
