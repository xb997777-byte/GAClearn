const router = require('../../utils/router');
const {
  BOOK_SOURCES,
  LEARNING_PATHS,
  GUIDE_SUMMARIES
} = require('../../utils/grammar-guide-outline');
const { withThemePage } = require('../../utils/theme-manager');

Page(withThemePage({
  data: {
    books: BOOK_SOURCES,
    paths: LEARNING_PATHS,
    volumes: GUIDE_SUMMARIES
  },

  handleOpenVolume(event) {
    const moduleId = event.currentTarget.dataset.moduleId;
    if (!moduleId) {
      return;
    }
    router.go(`/pages/grammar-guide-volume/index?id=${moduleId}`);
  }
}));
