const router = require('../../utils/router');
const { withThemePage } = require('../../utils/theme-manager');

function getGuideHelpers() {
  return require('../../utils/grammar-guide-data');
}

function buildNavigation(seriesId, summaries) {
  const currentIndex = summaries.findIndex((item) => item.id === seriesId);
  return {
    previous: currentIndex > 0 ? summaries[currentIndex - 1] : null,
    next: currentIndex >= 0 && currentIndex < summaries.length - 1 ? summaries[currentIndex + 1] : null
  };
}

function decorateVolumeDetail(volumeDetail) {
  return Object.assign({}, volumeDetail, {
    chapters: (volumeDetail.chapters || []).map((chapter, index) => Object.assign({}, chapter, {
      expanded: index === 0
    }))
  });
}

Page(withThemePage({
  data: {
    volumeDetail: null,
    previousVolume: null,
    nextVolume: null
  },

  onLoad(options) {
    const moduleId = options && options.id ? options.id : '';
    const { getGuideSeriesById, getGuideSeriesSummaries } = getGuideHelpers();
    const sourceVolume = getGuideSeriesById(moduleId);
    if (!sourceVolume) {
      wx.showToast({ title: '未找到这一册内容', icon: 'none' });
      setTimeout(() => {
        router.back();
      }, 300);
      return;
    }

    const navigation = buildNavigation(moduleId, getGuideSeriesSummaries());
    this.setData({
      volumeDetail: decorateVolumeDetail(sourceVolume),
      previousVolume: navigation.previous,
      nextVolume: navigation.next
    });
  },

  handleJumpVolume(event) {
    const moduleId = event.currentTarget.dataset.moduleId;
    if (!moduleId) {
      return;
    }

    const { getGuideSeriesById, getGuideSeriesSummaries } = getGuideHelpers();
    const sourceVolume = getGuideSeriesById(moduleId);
    if (!sourceVolume) {
      return;
    }

    const navigation = buildNavigation(moduleId, getGuideSeriesSummaries());
    this.setData({
      volumeDetail: decorateVolumeDetail(sourceVolume),
      previousVolume: navigation.previous,
      nextVolume: navigation.next
    });
  },

  handleToggleChapter(event) {
    const chapterNo = event.currentTarget.dataset.chapterNo;
    const volumeDetail = this.data.volumeDetail;
    if (!volumeDetail || !chapterNo) {
      return;
    }

    const chapters = (volumeDetail.chapters || []).map((chapter) => (
      chapter.no === chapterNo
        ? Object.assign({}, chapter, { expanded: !chapter.expanded })
        : chapter
    ));

    this.setData({
      'volumeDetail.chapters': chapters
    });
  }
}));
