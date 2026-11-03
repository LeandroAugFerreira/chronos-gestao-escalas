export type Permissions = Record<string, string[] | null>
export type User = { id: string; username: string; organization_id: string; permissions: Permissions }
export type Page<T> = { items: T[]; total: number; page: number; page_size: number }
export type Unit = { id: string; name: string; operation: string; timezone: string; revision: number }
export type Department = { id: string; unit_id: string; name: string; group: string; operation: string; cost_center: string; revision: number }
export type Catalog = { id: string; name: string; revision?: number; description?: string; legal_status?: string; configuration?: { cycle?: string[]; shift_minutes?: number } }
export type Employee = { id: string; organization_id: string; unit_id: string; department_id: string; job_role_id: string; name: string; registration: string; status: 'active' | 'inactive'; synthetic: boolean; revision: number }
export type Organization = { id: string; name: string; segment: string; timezone: string; operation: string; is_demo: boolean }
export type Overview = {
  organization: Organization; source: 'database'; as_of: string; unit_id: string | null;
  employee_count: number; active_count: number; inactive_count: number; unit_count: number; department_count: number;
  weekly_average_hours: number | null;
  departments: { id: string; name: string; group: string; unit_id: string; employee_count: number }[];
  regimes: { name: string; employee_count: number }[]; notices: string[];
}
export type Audit = { id: string; actor_id: string | null; action: string; entity_type: string; entity_id: string; correlation_id: string; created_at: string; details: Record<string, unknown> }
export type Account = { id: string; username: string; active: boolean }
export const catalogLabels: Record<string, string> = { 'job-roles': 'Funções', skills: 'Competências', qualifications: 'Qualificações', 'work-patterns': 'Jornadas de referência' }
export function permits(user: User | null, permission: string, unit?: string) {
  if (!user || !(permission in user.permissions)) return false
  const scope = user.permissions[permission]
  return scope === null || (unit === undefined ? scope.length > 0 : scope.includes(unit))
}
export function globalPermission(user: User | null, permission: string) {
  return !!user && permission in user.permissions && user.permissions[permission] === null
}
