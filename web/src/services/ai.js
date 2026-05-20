import { request } from '../lib/request';

const LONG_AI_TIMEOUT = 120000;

function req(url, method = 'GET', data = null, timeout = LONG_AI_TIMEOUT, params = null) {
  return request({
    url,
    method,
    data,
    timeout,
    params,
  });
}

export const getCapabilities = () => req('/api/v1/ai/capabilities', 'GET');
export const grammarTutor = (data = {}) => req('/api/v1/ai/grammar/tutor', 'POST', data);
export const getMcpManifest = () => req('/api/v1/ai/mcp/manifest', 'GET');
export const callMcpTool = (data = {}) => req('/api/v1/ai/mcp/tools/call', 'POST', data);
export const readMcpResource = (data = {}) => req('/api/v1/ai/mcp/resources/read', 'POST', data);
export const explainWord = (data = {}) => req('/api/v1/ai/words/explain', 'POST', data);
export const getStudyCoach = (data = {}) => req('/api/v1/ai/study-coach', 'POST', data);
export const replanStudyPlan = (data = {}) => req('/api/v1/ai/plans/replan', 'POST', data);
export const getPlanReplanRun = (runId) => req(`/api/v1/ai/plans/replan/runs/${encodeURIComponent(runId)}`, 'GET');
export const getAiRun = (runId) => req(`/api/v1/ai/runs/${encodeURIComponent(runId)}`, 'GET');
export const getAiRunSteps = (runId) => req(`/api/v1/ai/runs/${encodeURIComponent(runId)}/steps`, 'GET');
export const getAiRunArtifacts = (runId) => req(`/api/v1/ai/runs/${encodeURIComponent(runId)}/artifacts`, 'GET');
export const retryAiRun = (runId, data = {}) => req(`/api/v1/ai/runs/${encodeURIComponent(runId)}/retry`, 'POST', data);
export const resumeAiRun = (runId, data = {}) => req(`/api/v1/ai/runs/${encodeURIComponent(runId)}/resume`, 'POST', data);
export const cancelAiRun = (runId, data = {}) => req(`/api/v1/ai/runs/${encodeURIComponent(runId)}/cancel`, 'POST', data);
export const approveAiRun = (runId, data = {}) => req(`/api/v1/ai/runs/${encodeURIComponent(runId)}/approve`, 'POST', data);
export const runRetrievalOrchestrator = (data = {}) => req('/api/v1/ai/agents/retrieval-orchestrator', 'POST', data);
export const getWrongWordsReview = (data = {}) => req('/api/v1/ai/wrong-words/review', 'POST', data);
export const correctWriting = (data = {}) => req('/api/v1/ai/writing/correct', 'POST', data);
export const generateWritingPrompt = (data = {}) => req('/api/v1/ai/writing/prompt', 'POST', data);
export const evaluateTranslation = (data = {}) => req('/api/v1/ai/translation/evaluate', 'POST', data);
export const getGrammarGuide = () => req('/api/v1/ai/grammar/guide', 'GET');
export const ragSearch = (data = {}) => req('/api/v1/ai/rag/search', 'POST', data);
export const getRagIndexStatus = () => req('/api/v1/ai/rag/index-status', 'GET');
export const syncRagIndex = (data = {}) => req('/api/v1/ai/rag/index-sync', 'POST', data);
export const evaluateRagRecall = (data = {}) => req('/api/v1/ai/rag/recall-evaluate', 'POST', data);
export const vectorRagSearch = (data = {}) => req('/api/v1/ai/rag/vector-search', 'POST', data);
export const getScenarioTemplates = () => req('/api/v1/ai/scenario/templates', 'GET');
export const scenarioDialogue = (data = {}) => req('/api/v1/ai/scenario/dialogue', 'POST', data);
export const getAgentsBrief = () => req('/api/v1/ai/agents/brief', 'GET');
export const getQuality = () => req('/api/v1/ai/quality', 'GET');
export const getObservability = () => req('/api/v1/ai/observability', 'GET');
export const getProfileMemory = () => req('/api/v1/ai/profile-memory', 'GET');
export const refreshProfileMemory = (data = {}) => req('/api/v1/ai/profile-memory', 'POST', data);
export const getEvaluations = (params = {}) => req('/api/v1/ai/evaluations', 'GET', null, LONG_AI_TIMEOUT, params);
export const getEvaluationRunDetail = (runId) => req(`/api/v1/ai/evaluations/runs/${encodeURIComponent(runId)}`, 'GET');
export const replayEvaluationRun = (runId, data = {}) => req(`/api/v1/ai/evaluations/runs/${encodeURIComponent(runId)}/replay`, 'POST', data);
export const getReports = () => req('/api/v1/ai/reports', 'GET');
export const getConversations = (params = {}) => req('/api/v1/ai/conversations', 'GET', null, LONG_AI_TIMEOUT, params);
export const askConversation = (data = {}) => req('/api/v1/ai/conversations/ask', 'POST', data);
export const getConversationDetail = (conversationId) => req(`/api/v1/ai/conversations/${conversationId}`, 'GET');
export const submitAiFeedback = (data = {}) => req('/api/v1/ai/feedback', 'POST', data);
