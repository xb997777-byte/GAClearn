const { request } = require('../request');

const WORD_AI_TIMEOUT = 45000;
const STUDY_AI_TIMEOUT = 45000;
const WRONG_WORD_AI_TIMEOUT = 45000;
const LONG_AI_TIMEOUT = 60000;

function getCapabilities() {
  return request({
    url: '/ai/capabilities',
    method: 'GET'
  });
}

function grammarTutor(data = {}) {
  return request({
    url: '/ai/grammar/tutor',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function getMcpManifest() {
  return request({
    url: '/ai/mcp/manifest',
    method: 'GET'
  });
}

function callMcpTool(data = {}) {
  return request({
    url: '/ai/mcp/tools/call',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function readMcpResource(data = {}) {
  return request({
    url: '/ai/mcp/resources/read',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function explainWord(data) {
  return request({
    url: '/ai/words/explain',
    method: 'POST',
    data,
    timeout: WORD_AI_TIMEOUT
  });
}

function getStudyCoach(data = {}) {
  return request({
    url: '/ai/study-coach',
    method: 'POST',
    data,
    timeout: STUDY_AI_TIMEOUT
  });
}

function replanStudyPlan(data = {}) {
  return request({
    url: '/ai/plans/replan',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function runRetrievalOrchestrator(data = {}) {
  return request({
    url: '/ai/agents/retrieval-orchestrator',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function getWrongWordsReview(data = {}) {
  return request({
    url: '/ai/wrong-words/review',
    method: 'POST',
    data,
    timeout: WRONG_WORD_AI_TIMEOUT
  });
}

function correctWriting(data = {}) {
  return request({
    url: '/ai/writing/correct',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function generateWritingPrompt(data = {}) {
  return request({
    url: '/ai/writing/prompt',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function evaluateTranslation(data = {}) {
  return request({
    url: '/ai/translation/evaluate',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function getGrammarGuide() {
  return request({
    url: '/ai/grammar/guide',
    method: 'GET',
    timeout: STUDY_AI_TIMEOUT
  });
}

function ragSearch(data = {}) {
  return request({
    url: '/ai/rag/search',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function getRagIndexStatus() {
  return request({
    url: '/ai/rag/index-status',
    method: 'GET',
    timeout: STUDY_AI_TIMEOUT
  });
}

function syncRagIndex(data = {}) {
  return request({
    url: '/ai/rag/index-sync',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function evaluateRagRecall(data = {}) {
  return request({
    url: '/ai/rag/recall-evaluate',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function vectorRagSearch(data = {}) {
  return request({
    url: '/ai/rag/vector-search',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function getScenarioTemplates() {
  return request({
    url: '/ai/scenario/templates',
    method: 'GET',
    timeout: STUDY_AI_TIMEOUT
  });
}

function scenarioDialogue(data = {}) {
  return request({
    url: '/ai/scenario/dialogue',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function getAgentsBrief() {
  return request({
    url: '/ai/agents/brief',
    method: 'GET',
    timeout: STUDY_AI_TIMEOUT
  });
}

function getQuality() {
  return request({
    url: '/ai/quality',
    method: 'GET'
  });
}

function getObservability() {
  return request({
    url: '/ai/observability',
    method: 'GET'
  });
}

function getProfileMemory() {
  return request({
    url: '/ai/profile-memory',
    method: 'GET'
  });
}

function refreshProfileMemory(data = {}) {
  return request({
    url: '/ai/profile-memory',
    method: 'POST',
    data,
    timeout: STUDY_AI_TIMEOUT
  });
}

function getEvaluations(params = {}) {
  const query = [];
  if (params.case_type) {
    query.push(`case_type=${encodeURIComponent(params.case_type)}`);
  }
  if (params.failed_only) {
    query.push('failed_only=1');
  }
  if (params.limit) {
    query.push(`limit=${encodeURIComponent(params.limit)}`);
  }
  return request({
    url: `/ai/evaluations${query.length ? `?${query.join('&')}` : ''}`,
    method: 'GET'
  });
}

function getEvaluationRunDetail(runId) {
  return request({
    url: `/ai/evaluations/runs/${encodeURIComponent(runId)}`,
    method: 'GET'
  });
}

function replayEvaluationRun(runId, data = {}) {
  return request({
    url: `/ai/evaluations/runs/${encodeURIComponent(runId)}/replay`,
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function getConversationDetail(conversationId) {
  return request({
    url: `/ai/conversations/${encodeURIComponent(conversationId)}`,
    method: 'GET'
  });
}

function runEvaluations(data = {}) {
  return request({
    url: '/ai/evaluations',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function listReports(params = {}) {
  const query = [];
  if (params.report_type) {
    query.push(`report_type=${encodeURIComponent(params.report_type)}`);
  }
  if (params.limit) {
    query.push(`limit=${encodeURIComponent(params.limit)}`);
  }
  if (params.include_compare) {
    query.push('include_compare=1');
  }
  return request({
    url: `/ai/reports${query.length ? `?${query.join('&')}` : ''}`,
    method: 'GET'
  });
}

function generateReport(data = {}) {
  return request({
    url: '/ai/reports',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function listConversations(params = {}) {
  const query = [];
  if (params.feature_type) {
    query.push(`feature_type=${encodeURIComponent(params.feature_type)}`);
  }
  if (params.limit) {
    query.push(`limit=${encodeURIComponent(params.limit)}`);
  }
  return request({
    url: `/ai/conversations${query.length ? `?${query.join('&')}` : ''}`,
    method: 'GET'
  });
}

function askConversation(data = {}) {
  return request({
    url: '/ai/conversations/ask',
    method: 'POST',
    data,
    timeout: LONG_AI_TIMEOUT
  });
}

function submitFeedback(data = {}) {
  return request({
    url: '/ai/feedback',
    method: 'POST',
    data
  });
}

module.exports = {
  getCapabilities,
  grammarTutor,
  getMcpManifest,
  callMcpTool,
  readMcpResource,
  explainWord,
  getStudyCoach,
  replanStudyPlan,
  runRetrievalOrchestrator,
  getWrongWordsReview,
  correctWriting,
  generateWritingPrompt,
  evaluateTranslation,
  getGrammarGuide,
  ragSearch,
  getRagIndexStatus,
  syncRagIndex,
  evaluateRagRecall,
  vectorRagSearch,
  getScenarioTemplates,
  scenarioDialogue,
  getAgentsBrief,
  getQuality,
  getObservability,
  getProfileMemory,
  refreshProfileMemory,
  getEvaluations,
  getEvaluationRunDetail,
  replayEvaluationRun,
  runEvaluations,
  listReports,
  generateReport,
  listConversations,
  getConversationDetail,
  askConversation,
  submitFeedback
};
