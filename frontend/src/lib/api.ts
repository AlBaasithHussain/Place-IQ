import axios from "axios";

export const TOKEN_KEY = "preppilot_token";
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const DOCS_URL = `${API_BASE_URL.replace(/\/$/, "")}/docs`;

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

const PUBLIC_REQUEST_PATHS = ["/auth/login", "/auth/register", "/health"];

api.interceptors.request.use((config) => {
  const url = config.url ?? "";
  const isPublic = PUBLIC_REQUEST_PATHS.some((path) => url.includes(path));
  const token = localStorage.getItem(TOKEN_KEY);
  if (token && !isPublic) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

api.interceptors.response.use(undefined, (error) => {
  if (error.response?.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    const path = window.location.pathname;
    if (!path.startsWith("/login") && !path.startsWith("/register")) {
      window.location.assign("/login");
    }
  }
  return Promise.reject(error);
});

// ---------- Types ----------
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RegisterInput {
  name: string;
  email: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface StudentProfile {
  user_id: number;
  college: string | null;
  degree: string | null;
  branch: string | null;
  graduation_year: number | null;
  target_role: string | null;
}

export interface ProfileInput {
  college?: string | null;
  degree?: string | null;
  branch?: string | null;
  graduation_year?: number | null;
  target_role?: string | null;
}

export interface ParsedResume {
  name: string | null;
  email: string | null;
  education: string[];
  skills: string[];
  programming_languages: string[];
  frameworks: string[];
  databases: string[];
  tools: string[];
  projects: string[];
  certifications: string[];
  experience: string[];
}

export interface ResumeSummary {
  id: number;
  original_filename: string;
  file_size: number;
  created_at: string;
  name: string | null;
  email: string | null;
}

export interface ResumeDetail {
  id: number;
  user_id: number;
  original_filename: string;
  file_size: number;
  mime_type: string;
  created_at: string;
  raw_text: string;
  parsed_data: ParsedResume;
}

export interface JobAnalysis {
  job_title: string;
  required_skills: string[];
  preferred_skills: string[];
  programming_languages: string[];
  frameworks: string[];
  databases: string[];
  cloud_technologies: string[];
  tools: string[];
  soft_skills: string[];
  experience_requirements: string[];
  education_requirements: string[];
}

export interface JobSummary {
  id: number;
  job_title: string;
  analysis_engine: string;
  created_at: string;
}

export interface JobDetail extends JobAnalysis {
  id: number;
  user_id: number;
  original_text: string;
  analysis_engine: string;
  created_at: string;
  updated_at: string;
}

export type SkillStatus = "match" | "partial" | "missing";
export type RequirementType = "required" | "preferred" | "soft";

export interface SkillComparison {
  skill: string;
  status: SkillStatus;
  requirement_type: RequirementType;
}

export interface BreakdownPart {
  weight: number;
  credit: number;
  points: number;
  details: Record<string, string | number | null>;
}

export interface ScoreBreakdown {
  required_skills: BreakdownPart;
  preferred_skills: BreakdownPart;
  projects_experience: BreakdownPart;
  soft_skills: BreakdownPart;
}

export interface MatchResult {
  score: number;
  matching_skills: string[];
  partial_skills: string[];
  missing_skills: string[];
  bonus_skills: string[];
  comparisons: SkillComparison[];
  breakdown: ScoreBreakdown;
  explanation: string;
}

export interface MatchDetail extends MatchResult {
  id: number;
  user_id: number;
  resume_id: number;
  job_id: number;
  created_at: string;
}

export interface AnalysisSummary {
  id: number;
  resume_id: number;
  job_id: number;
  score: number;
  created_at: string;
}

export type PriorityLevel = "high" | "medium" | "low";

export interface RoadmapTask {
  id: number;
  roadmap_id: number;
  day: number;
  title: string;
  priority: PriorityLevel;
  estimated_minutes: number;
  learning_topics: string[];
  practice_tasks: string[];
  mini_project: string;
  completed: boolean;
  completed_at: string | null;
}

export interface RoadmapDetail {
  id: number;
  user_id: number;
  resume_id: number;
  job_id: number;
  analysis_id: number;
  job_title: string;
  match_score: number;
  duration_days: number;
  hours_per_day: number;
  generation_engine: string;
  priority_skills: string[];
  summary: string;
  created_at: string;
  tasks: RoadmapTask[];
  total_estimated_minutes: number;
  completed_count: number;
  progress_percentage: number;
}

export interface RoadmapSummary {
  id: number;
  analysis_id: number;
  job_title: string;
  match_score: number;
  duration_days: number;
  generation_engine: string;
  created_at: string;
  progress_percentage: number;
}

export interface RoadmapGenerateRequest {
  analysis_id: number;
  duration_days: 7 | 14;
  hours_per_day: number;
}

export type QuestionCategory =
  | "technical"
  | "hr"
  | "behavioral"
  | "project_based"
  | "problem_solving";

export type InterviewStatus = "in_progress" | "completed";

export interface InterviewQuestion {
  id: number;
  interview_id: number;
  position: number;
  category: QuestionCategory;
  question: string;
  focus_skill: string;
  answer: string | null;
  answered_at: string | null;
}

export interface InterviewDetail {
  id: number;
  user_id: number;
  resume_id: number;
  job_id: number;
  job_title: string;
  question_count: number;
  generation_engine: string;
  status: InterviewStatus;
  created_at: string;
  completed_at: string | null;
  questions: InterviewQuestion[];
  answered_count: number;
  progress_percentage: number;
  current_question_number: number | null;
  is_complete: boolean;
  has_evaluation: boolean;
}

export interface InterviewSummary {
  id: number;
  resume_id: number;
  job_id: number;
  job_title: string;
  question_count: number;
  generation_engine: string;
  status: InterviewStatus;
  created_at: string;
  progress_percentage: number;
  has_evaluation: boolean;
}

export interface InterviewStartRequest {
  resume_id: number;
  job_id: number;
  question_count: number;
}

export interface AnswerEvaluation {
  id: number;
  evaluation_id: number;
  question_id: number;
  position: number;
  category: QuestionCategory;
  question: string;
  answer: string;
  focus_skill: string;
  score: number;
  technical_accuracy: number;
  relevance: number;
  completeness: number;
  clarity: number;
  strengths: string[];
  weaknesses: string[];
  suggested_improvement: string;
  model_answer: string;
}

export interface EvaluationResult {
  id: number;
  interview_id: number;
  job_title: string;
  overall_score: number;
  generation_engine: string;
  overall_summary: string;
  overall_strengths: string[];
  overall_weaknesses: string[];
  suggested_improvements: string[];
  question_count: number;
  evaluated_answer_count: number;
  answer_evaluations: AnswerEvaluation[];
  created_at: string;
  updated_at: string;
}

// ---------- Endpoints ----------
export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/api/v1/health");
  return data;
}

export async function register(input: RegisterInput): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/api/v1/auth/register", input);
  return data;
}

export async function login(input: LoginInput): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>("/api/v1/auth/login", input);
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/api/v1/auth/me");
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/api/v1/auth/logout");
}

export async function getProfile(): Promise<StudentProfile> {
  const { data } = await api.get<StudentProfile>("/api/v1/profile/me");
  return data;
}

export async function updateProfile(input: ProfileInput): Promise<StudentProfile> {
  const { data } = await api.put<StudentProfile>("/api/v1/profile/me", input);
  return data;
}

export async function uploadResume(file: File): Promise<ResumeDetail> {
  const form = new FormData();
  form.append("file", file);
  // Axios detects FormData and sets the multipart boundary automatically.
  const { data } = await api.post<ResumeDetail>("/api/v1/resumes/upload", form);
  return data;
}

export async function listResumes(): Promise<ResumeSummary[]> {
  const { data } = await api.get<ResumeSummary[]>("/api/v1/resumes");
  return data;
}

export async function getResume(id: number): Promise<ResumeDetail> {
  const { data } = await api.get<ResumeDetail>(`/api/v1/resumes/${id}`);
  return data;
}

export async function analyzeJob(text: string): Promise<JobDetail> {
  const { data } = await api.post<JobDetail>("/api/v1/jobs/analyze", { text });
  return data;
}

export async function listJobs(): Promise<JobSummary[]> {
  const { data } = await api.get<JobSummary[]>("/api/v1/jobs");
  return data;
}

export async function getJob(id: number): Promise<JobDetail> {
  const { data } = await api.get<JobDetail>(`/api/v1/jobs/${id}`);
  return data;
}

export async function createMatch(resumeId: number, jobId: number): Promise<MatchDetail> {
  const { data } = await api.post<MatchDetail>("/api/v1/analysis/match", {
    resume_id: resumeId,
    job_id: jobId,
  });
  return data;
}

export async function getAnalysis(id: number): Promise<MatchDetail> {
  const { data } = await api.get<MatchDetail>(`/api/v1/analysis/${id}`);
  return data;
}

export async function listAnalyses(): Promise<AnalysisSummary[]> {
  const { data } = await api.get<AnalysisSummary[]>("/api/v1/analysis");
  return data;
}

export async function generateRoadmap(input: RoadmapGenerateRequest): Promise<RoadmapDetail> {
  const { data } = await api.post<RoadmapDetail>("/api/v1/roadmaps/generate", input);
  return data;
}

export async function getRoadmap(id: number): Promise<RoadmapDetail> {
  const { data } = await api.get<RoadmapDetail>(`/api/v1/roadmaps/${id}`);
  return data;
}

export async function listRoadmaps(): Promise<RoadmapSummary[]> {
  const { data } = await api.get<RoadmapSummary[]>("/api/v1/roadmaps");
  return data;
}

export async function updateRoadmapTask(
  roadmapId: number,
  taskId: number,
  completed: boolean,
): Promise<RoadmapDetail> {
  const { data } = await api.patch<RoadmapDetail>(
    `/api/v1/roadmaps/${roadmapId}/tasks/${taskId}`,
    { completed },
  );
  return data;
}

export async function startInterview(input: InterviewStartRequest): Promise<InterviewDetail> {
  const { data } = await api.post<InterviewDetail>("/api/v1/interviews/start", input);
  return data;
}

export async function getInterview(id: number): Promise<InterviewDetail> {
  const { data } = await api.get<InterviewDetail>(`/api/v1/interviews/${id}`);
  return data;
}

export async function listInterviews(): Promise<InterviewSummary[]> {
  const { data } = await api.get<InterviewSummary[]>("/api/v1/interviews");
  return data;
}

export async function answerInterviewQuestion(
  interviewId: number,
  questionId: number,
  answer: string,
): Promise<InterviewDetail> {
  const { data } = await api.post<InterviewDetail>(
    `/api/v1/interviews/${interviewId}/answer`,
    { question_id: questionId, answer },
  );
  return data;
}

export async function evaluateInterview(id: number): Promise<EvaluationResult> {
  const { data } = await api.post<EvaluationResult>(
    `/api/v1/interviews/${id}/evaluate`,
  );
  return data;
}

export async function getInterviewResults(id: number): Promise<EvaluationResult> {
  const { data } = await api.get<EvaluationResult>(
    `/api/v1/interviews/${id}/results`,
  );
  return data;
}

export interface DashboardOverview {
  resume_score: number;
  resume_file_name: string | null;
  job_match_score: number;
  interview_score: number;
  skills_learned: number;
  learned_skills: string[];
  latest_analysis_id: number | null;
  latest_interview_id: number | null;
}

export interface DashboardSkill {
  skill: string;
  requirement_type: string | null;
}

export interface DashboardSkillAnalysis {
  analysis_id: number | null;
  job_title: string | null;
  strong_skills: DashboardSkill[];
  partial_skills: DashboardSkill[];
  missing_skills: DashboardSkill[];
}

export interface DashboardLearningProgress {
  has_roadmap: boolean;
  roadmap_id: number | null;
  job_title: string | null;
  duration_days: number;
  total_tasks: number;
  completed_tasks: number;
  remaining_tasks: number;
  progress_percentage: number;
  priority_skills: string[];
  summary: string;
}

export interface DashboardInterviewStats {
  sessions: number;
  completed_sessions: number;
  questions_attempted: number;
  questions_total: number;
  evaluated_sessions: number;
  average_score: number;
  latest_score: number;
}

export interface RecentJob {
  id: number;
  job_title: string;
  analysis_engine: string;
  created_at: string;
  match_score: number | null;
}

export interface ScoreTrendPoint {
  label: string;
  value: number;
}

export interface DashboardTrends {
  match_scores: ScoreTrendPoint[];
  interview_scores: ScoreTrendPoint[];
}

export interface ReadinessComponent {
  key: string;
  label: string;
  weight: number;
  score: number;
  contribution: number;
}

export interface PlacementReadiness {
  score: number;
  band: string;
  formula: string;
  components: ReadinessComponent[];
}

export interface TargetSkillFrequency {
  skill: string;
  job_count: number;
  total_jobs: number;
  frequency_percentage: number;
  requirement_types: string[];
  required_count: number;
  preferred_count: number;
}

export interface TargetSkillAnalysis {
  total_jobs: number;
  skills: TargetSkillFrequency[];
}

export interface DashboardData {
  has_data: boolean;
  overview: DashboardOverview;
  readiness: PlacementReadiness;
  skill_analysis: DashboardSkillAnalysis;
  learning_progress: DashboardLearningProgress;
  interview: DashboardInterviewStats;
  recent_jobs: RecentJob[];
  target_skills: TargetSkillAnalysis;
  trends: DashboardTrends;
}

export async function getDashboard(): Promise<DashboardData> {
  const { data } = await api.get<DashboardData>("/api/v1/dashboard");
  return data;
}

// Turn FastAPI's validation errors / messages into a single readable string.
export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { detail?: string | Array<{ msg?: string }> }
      | undefined;

    if (data?.detail) {
      if (typeof data.detail === "string") return data.detail;
      if (Array.isArray(data.detail)) {
        return data.detail.map((item) => item.msg ?? "Invalid value").join(", ");
      }
    }
    if (!error.response) {
      return "Cannot reach the server. Is the backend running?";
    }
    return error.message;
  }
  return "Something went wrong. Please try again.";
}
