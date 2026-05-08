Component({
  properties: {
    evidence: {
      type: Object,
      value: null
    },
    title: {
      type: String,
      value: 'AI 证据区'
    }
  },

  data: {
    displayEvidence: null
  },

  observers: {
    evidence(value) {
      this.setData({
        displayEvidence: this.normalizeEvidence(value)
      });
    }
  },

  methods: {
    normalizeEvidence(evidence) {
      if (!evidence) {
        return null;
      }
      const statusMapping = {
        success: '成功',
        succeeded: '成功',
        ok: '成功',
        completed: '已完成',
        running: '运行中',
        pending: '待处理',
        queued: '排队中',
        failed: '失败',
        failure: '失败',
        error: '失败'
      };
      const copy = Object.assign({}, evidence);
      copy.tools_used = (copy.tools_used || []).map((item) => Object.assign({}, item, {
        args_text: item && item.args ? JSON.stringify(item.args) : ''
      }));
      copy.trace_timeline = (copy.trace_timeline || []).map((item) => Object.assign({}, item, {
        meta_text: item && item.meta ? JSON.stringify(item.meta) : '',
        status_text: statusMapping[item && item.status] || (item && item.status) || '成功'
      }));
      copy.observability = copy.observability
        ? Object.assign({}, copy.observability, {
          status_text: statusMapping[copy.observability.status] || copy.observability.status || '成功'
        })
        : null;
      return copy;
    }
  }
});
