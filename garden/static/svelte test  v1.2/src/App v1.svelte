<script>
  import { onMount } from 'svelte';
  import { session, setSession, initializeGuestSession } from './stores/session.js';
  import markdownConfig from '../JAVASCRIPT_FUNCTIONS_AND_APIS.md?raw';

  function getMarkdownValue(key, fallbackValue) {
    const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = markdownConfig.match(new RegExp(`^${escapedKey}:[ \\t]*(.*)$`, 'm'));
    return match?.[1]?.trim() || fallbackValue;
  }

  function normalizeLookApiBaseUrl(urlValue) {
    const normalizedUrl = String(urlValue ?? '').trim().replace(/\/+$/, '');

    if (!normalizedUrl) {
      return '';
    }
 
    const segments = normalizedUrl.split('/');
    const secondLastSegment = segments[segments.length - 2];

    if (secondLastSegment === 'look') {
      segments.pop();
    }

    return `${segments.join('/')}/`;
  }

  function extractDefaultCollectionStr(urlValue, fallbackValue = '11111') {
    const normalizedUrl = String(urlValue ?? '').trim().replace(/\/+$/, '');

    if (!normalizedUrl) {
      return fallbackValue;
    }

    const segments = normalizedUrl.split('/');
    const lastSegment = segments[segments.length - 1] || '';
    const secondLastSegment = segments[segments.length - 2];

    return secondLastSegment === 'look' ? lastSegment : fallbackValue;
  }

  const API_BASE_URL = getMarkdownValue(
    'API_BASE_URL',
    'http://127.0.0.1:8000/garden/look/ZN6RF9/'
  );
  const UPLOAD_API_URL = getMarkdownValue(
    'UPLOAD_API_URL',
    'http://127.0.0.1:8000/apis/upload_to_imbb/'
  );
  const UPLOAD_IMAGE_FIELD = getMarkdownValue('UPLOAD_IMAGE_FIELD', '');
  const API_USERNAME = getMarkdownValue('API_USERNAME', '');
  const API_USER_ID = getMarkdownValue('API_USER_ID', '');
const EMAILJS_PUBLIC_KEY = 'kPR5fCmH0j3E0NSyr';
const EMAILJS_SERVICE_ID = 'service_jv335d7';
const ACCEPT_HEADER = 'application/json';
  const EMAILJS_TEMPLATE_ID = 'template_hzlk188';
  const EMAILJS_REPLY_TO = 'dayo_john16@yahoo.com';
  const EMAILJS_TO_NAME = 'dayo_john16@yahoo.com';
  const SUGGESTION_COOLDOWN_MS = 60 * 60 * 1000;
  const SUGGESTION_LAST_SENT_KEY_PREFIX = 'postcard_last_suggestion_at';
  const LOCAL_STORAGE_USERNAME_KEY = getMarkdownValue(
    'LOCAL_STORAGE_USERNAME_KEY',
    'postcard_username'
  );
  const LOCAL_STORAGE_USER_ID_KEY = getMarkdownValue('LOCAL_STORAGE_USER_ID_KEY', 'postcard_user_id');
  const LOCAL_STORAGE_SESSION_USER_KEY = getMarkdownValue('LOCAL_STORAGE_SESSION_USER_KEY', 'user');
  const LOCAL_STORAGE_SESSION_USER_ID_KEY = getMarkdownValue('LOCAL_STORAGE_SESSION_USER_ID_KEY', 'userID');
  const LOCAL_STORAGE_SESSION_TOKEN_KEY = getMarkdownValue('LOCAL_STORAGE_SESSION_TOKEN_KEY', 'token');
  const LOCAL_STORAGE_CONTACT_KEY = getMarkdownValue('LOCAL_STORAGE_CONTACT_KEY', 'postcard_contact');
  const LOCAL_STORAGE_TOUR_NAME_KEY = getMarkdownValue(
    'LOCAL_STORAGE_TOUR_NAME_KEY',
    'postcard_tour_name'
  );
  const LOCAL_STORAGE_TOUR_DATE_KEY = getMarkdownValue(
    'LOCAL_STORAGE_TOUR_DATE_KEY',
    'postcard_tour_date'
  );
  const LOCAL_STORAGE_THEME_KEY = getMarkdownValue('LOCAL_STORAGE_THEME_KEY', 'postcard_theme');
  const LOCAL_STORAGE_LANGUAGE_KEY = getMarkdownValue('LOCAL_STORAGE_LANGUAGE_KEY', 'postcard_language');
  const POSTCARD_DETAILS_API_BASE_URL = normalizeLookApiBaseUrl(API_BASE_URL);
  const DEFAULT_COLLECTION_STR = extractDefaultCollectionStr(API_BASE_URL, '11111');
  const LOADING_DELAY_MS = Number(getMarkdownValue('LOADING_DELAY_MS', '1500')) || 1500;
  const MAIN_IMAGE_URL = getMarkdownValue('MAIN_IMAGE_URL', 'https://placehold.co/960x540/png');
  const POSTCARD_MEMORY_IMAGE_URLS = [
    getMarkdownValue('COLLECTION_1_URL', 'https://placehold.co/640x400/png?text=Postcard+1'),
    getMarkdownValue('COLLECTION_2_URL', 'https://placehold.co/640x400/png?text=Postcard+2'),
    getMarkdownValue('COLLECTION_3_URL', 'https://placehold.co/640x400/png?text=Postcard+3'),
    getMarkdownValue('COLLECTION_4_URL', 'https://placehold.co/640x400/png?text=Postcard+4')
  ];
  const MEMORY_PROMPT_STORAGE_KEY = 'postcard_memory_prompt_index';
  const MEMORY_PROMPTS_BY_LANGUAGE = {
    en: [
      "The memory I'll always keep from here is _____.",
      "I'll never forget this place because _____.",
      'This place will always remind me of _____.',
      'When I think of this place, I remember _____.',
      'What made this place unforgettable was _____.',
      'The moment that stayed with me here was _____.',
      'This place meant so much to me because _____.',
      "One thing I'll never forget about this place is _____."
    ],
    fr: [
      'Le souvenir que je garderai toujours d’ici est _____.',
      'Je n’oublierai jamais cet endroit parce que _____.',
      'Cet endroit me rappellera toujours _____.',
      'Quand je pense à cet endroit, je me souviens de _____.',
      'Ce qui a rendu cet endroit inoubliable, c’est _____.',
      'Le moment qui m’est resté ici est _____.',
      'Cet endroit comptait beaucoup pour moi parce que _____.',
      'Une chose que je n’oublierai jamais de cet endroit est _____.'
    ],
    ru: [
      'Воспоминание, которое я всегда сохраню отсюда, — _____.',
      'Я никогда не забуду это место, потому что _____.',
      'Это место всегда будет напоминать мне о _____.',
      'Когда я думаю об этом месте, я вспоминаю _____.',
      'Это место стало незабываемым из-за _____.',
      'Момент, который остался со мной здесь, — _____.',
      'Это место так много значило для меня, потому что _____.',
      'Одна вещь, которую я никогда не забуду об этом месте, — _____.'
    ],
    ko: [
      '이곳에서 가장 오래 기억에 남을 순간은 _____.',
      '이곳을 절대 잊지 못할 이유는 _____.',
      '이곳은 늘 _____를 떠올리게 해요.',
      '이곳을 생각하면 _____가 기억나요.',
      '이곳을 잊을 수 없게 만든 건 _____.',
      '여기서 가장 마음에 남은 순간은 _____.',
      '이곳이 특별했던 이유는 _____.',
      '이곳에서 절대 잊지 못할 한 가지는 _____.'
    ],
    zh: [
      '我会一直记得这里的回忆是 _____.',
      '我永远不会忘记这里，因为 _____.',
      '这个地方总会让我想起 _____.',
      '当我想到这里时，我会想起 _____.',
      '让这个地方难忘的是 _____.',
      '在这里最难忘的瞬间是 _____.',
      '这个地方对我意义重大，因为 _____.',
      '关于这个地方，我最不会忘记的是 _____.'
    ]
  };

  const TRANSLATIONS = {
    en: {
      brandTitle: 'Garden Home Postcard',
      welcome: 'Welcome, {name}',
      guest: 'Guest',
      themeToLight: 'Switch to light theme',
      themeToDark: 'Switch to dark theme',
      eyebrow: 'MEMORIES, COLLECTED AND SHARED',
      subtext: 'Collect moments, travel with ease, and share memories.',
      enterAccount: 'Create your account',
      username: 'Your User Name',
      userId: 'Your Passcode',
      enterUsername: 'Enter any username',
      enterUserId: 'Enter any Passcode',
      saveAndContinue: 'Save and Continue',
      loadingImage: 'Loading image...',
      scannedPostcardAlt: 'Scanned postcard',
      location: 'Location',
      collected: 'Collected',
      collector: 'Collector',
      uploading: 'Uploading...',
      uploadPicture: 'Upload picture',
      collectionMemory: 'Post Card Memories',
      noCollectionMemory: '',
      gridTitle: 'Once There, Now a Memory.',
      noPostcardData: 'No postcard data found for this account.',
      fetchError: 'Could not fetch data. Check username and userID.',
      memoryPromptFallback: "What's your memory about this place?",
      uploadNeedCredentials: 'Please set username and userID before uploading.',
      uploadFailed: 'Upload failed.',
      uploadResponseMissing: 'Upload response missing saved files list.',
      uploadingFiles: ({ count }) => `Uploading ${count} file${count > 1 ? 's' : ''}...`,
      uploadedFiles: ({ count }) => `Uploaded ${count} file${count > 1 ? 's' : ''} successfully.`,
      enterBothCredentials: 'Please enter both username and userID.',
      imagePreview: 'Image preview',
      suggestionPlaceholder: 'Tell or give us suggestions',
      sendSuggestion: 'Send suggestion',
      sendingSuggestion: 'Sending...',
      suggestionNeedText: 'Please enter your suggestion.',
      suggestionSent: 'Thanks for suggestions',
      suggestionFailed: 'Could not send suggestion right now.',
      bookIslandTour: 'Book island tour',
      islandTourTitle: 'Book your island tour',
      islandTourDescription: 'Leave your name and contact details and we will follow up with tour availability.',
      nameLabel: 'Name',
      contactLabel: 'Contact',
      dateLabel: 'Tour date',
      enterName: 'Enter your name',
      enterContact: 'Enter your contact',
      cancel: 'Cancel',
      submitBooking: 'Submit booking',
      bookingNeedName: 'Please enter your name.',
      bookingNeedContact: 'Please enter your contact details.',
      bookingNeedDate: 'Please choose a tour date.',
      bookingSaved: 'Tour request saved. We will contact you soon.'
    },
    fr: {
      brandTitle: 'Carte Postale Garden Home',
      welcome: 'Bienvenue, {name}',
      guest: 'Invité',
      themeToLight: 'Passer au thème clair',
      themeToDark: 'Passer au thème sombre',
      eyebrow: 'SOUVENIRS, RASSEMBLÉS ET PARTAGÉS',
      subtext: 'Collectez des moments, voyagez facilement et partagez vos souvenirs.',
      enterAccount: 'Entrez votre compte',
      username: 'Nom d’utilisateur',
      userId: 'Votre mot de passe',
      enterUsername: 'Entrez n’importe quel nom d’utilisateur',
      enterUserId: 'Entrez n’importe quel mot de passe',
      saveAndContinue: 'Enregistrer et continuer',
      loadingImage: 'Chargement de l’image...',
      scannedPostcardAlt: 'Carte postale scannée',
      location: 'Lieu',
      collected: 'Collecté',
      collector: 'Collectionneur',
      uploading: 'Téléversement...',
      uploadPicture: 'Téléverser une image',
      collectionMemory: 'Souvenirs de cartes postales',
      noCollectionMemory: 'Aucun souvenir de collection pour le moment.',
      gridTitle: 'Autrefois visité, aujourd’hui souvenir.',
      noPostcardData: 'Aucune donnée de carte postale trouvée pour ce compte.',
      fetchError: 'Impossible de récupérer les données. Vérifiez le nom d’utilisateur et l’ID utilisateur.',
      memoryPromptFallback: 'Quel est votre souvenir de cet endroit ?',
      uploadNeedCredentials: 'Veuillez définir le nom d’utilisateur et l’ID utilisateur avant de téléverser.',
      uploadFailed: 'Le téléversement a échoué.',
      uploadResponseMissing: 'La réponse de téléversement ne contient pas la liste des fichiers enregistrés.',
      uploadingFiles: ({ count }) => `Téléversement de ${count} fichier${count > 1 ? 's' : ''}...`,
      uploadedFiles: ({ count }) => `${count} fichier${count > 1 ? 's' : ''} téléversé${count > 1 ? 's' : ''} avec succès.`,
      enterBothCredentials: 'Veuillez saisir le nom d’utilisateur et l’ID utilisateur.',
      imagePreview: 'Aperçu de l’image',
      suggestionPlaceholder: 'Dites-nous ou donnez-nous des suggestions',
      sendSuggestion: 'Envoyer une suggestion',
      sendingSuggestion: 'Envoi...',
      suggestionNeedText: 'Veuillez saisir votre suggestion.',
      suggestionSent: 'Merci pour vos suggestions',
      suggestionFailed: 'Impossible d’envoyer la suggestion pour le moment.'
    },
    ru: {
      brandTitle: 'Открытка Garden Home',
      welcome: 'Добро пожаловать, {name}',
      guest: 'Гость',
      themeToLight: 'Переключить на светлую тему',
      themeToDark: 'Переключить на тёмную тему',
      eyebrow: 'ВОСПОМИНАНИЯ, СОБРАННЫЕ И ПОДЕЛЁННЫЕ',
      subtext: 'Собирайте моменты, путешествуйте с лёгкостью и делитесь воспоминаниями.',
      enterAccount: 'Введите данные аккаунта',
      username: 'Имя пользователя',
      userId: 'Ваш пароль',
      enterUsername: 'Введите любой логин',
      enterUserId: 'Введите любой пароль',
      saveAndContinue: 'Сохранить и продолжить',
      loadingImage: 'Загрузка изображения...',
      scannedPostcardAlt: 'Отсканированная открытка',
      location: 'Место',
      collected: 'Собрано',
      collector: 'Коллекционер',
      uploading: 'Загрузка...',
      uploadPicture: 'Загрузить изображение',
      collectionMemory: 'Воспоминания открытки',
      noCollectionMemory: 'Пока нет воспоминаний в коллекции.',
      gridTitle: 'Когда-то здесь, теперь воспоминание.',
      noPostcardData: 'Для этого аккаунта не найдены данные открытки.',
      fetchError: 'Не удалось получить данные. Проверьте имя пользователя и ID пользователя.',
      memoryPromptFallback: 'Какое у вас воспоминание об этом месте?',
      uploadNeedCredentials: 'Перед загрузкой укажите имя пользователя и ID пользователя.',
      uploadFailed: 'Загрузка не удалась.',
      uploadResponseMissing: 'В ответе загрузки отсутствует список сохранённых файлов.',
      uploadingFiles: ({ count }) => `Загрузка ${count} файл${count > 1 ? 'ов' : 'а'}...`,
      uploadedFiles: ({ count }) => `Успешно загружено ${count} файл${count > 1 ? 'ов' : ''}.`,
      enterBothCredentials: 'Введите имя пользователя и ID пользователя.',
      imagePreview: 'Предпросмотр изображения',
      suggestionPlaceholder: 'Расскажите нам или оставьте предложение',
      sendSuggestion: 'Отправить предложение',
      sendingSuggestion: 'Отправка...',
      suggestionNeedText: 'Пожалуйста, введите ваше предложение.',
      suggestionSent: 'Спасибо за предложение',
      suggestionFailed: 'Сейчас не удалось отправить предложение.'
    },
    ko: {
      brandTitle: '가든 홈 엽서',
      welcome: '{name}님, 환영합니다',
      guest: '게스트',
      themeToLight: '라이트 테마로 전환',
      themeToDark: '다크 테마로 전환',
      eyebrow: '추억을 모으고 함께 나눠요',
      subtext: '순간을 수집하고, 편하게 여행하며, 추억을 공유하세요.',
      enterAccount: '계정 정보를 입력하세요',
      username: '사용자 이름',
      userId: '패스코드',
      enterUsername: '아무 사용자 이름이나 입력하세요',
      enterUserId: '아무 패스코드를 입력하세요',
      saveAndContinue: '저장하고 계속',
      loadingImage: '이미지 불러오는 중...',
      scannedPostcardAlt: '스캔된 엽서',
      location: '위치',
      collected: '수집일',
      collector: '수집자',
      uploading: '업로드 중...',
      uploadPicture: '사진 업로드',
      collectionMemory: '컬렉션 메모리',
      noCollectionMemory: '아직 컬렉션 메모리가 없습니다.',
      gridTitle: '그때의 장소, 지금의 추억.',
      noPostcardData: '이 계정의 엽서 데이터를 찾을 수 없습니다.',
      fetchError: '데이터를 가져오지 못했습니다. 사용자 이름과 사용자 ID를 확인하세요.',
      memoryPromptFallback: '이 장소에 대한 당신의 추억은 무엇인가요?',
      uploadNeedCredentials: '업로드 전에 사용자 이름과 사용자 ID를 설정하세요.',
      uploadFailed: '업로드에 실패했습니다.',
      uploadResponseMissing: '업로드 응답에 저장된 파일 목록이 없습니다.',
      uploadingFiles: ({ count }) => `${count}개 파일 업로드 중...`,
      uploadedFiles: ({ count }) => `${count}개 파일 업로드 완료.`,
      enterBothCredentials: '사용자 이름과 사용자 ID를 모두 입력하세요.',
      imagePreview: '이미지 미리보기',
      suggestionPlaceholder: '건의사항을 입력하세요',
      sendSuggestion: '건의 보내기',
      sendingSuggestion: '전송 중...',
      suggestionNeedText: '건의사항을 입력해주세요.',
      suggestionSent: '건의해 주셔서 감사합니다',
      suggestionFailed: '지금은 건의를 보낼 수 없습니다.'
    },
    zh: {
      brandTitle: '花园之家明信片',
      welcome: '欢迎，{name}',
      guest: '访客',
      themeToLight: '切换到浅色主题',
      themeToDark: '切换到深色主题',
      eyebrow: '收集并分享回忆',
      subtext: '收集瞬间，轻松旅行，分享回忆。',
      enterAccount: '输入你的账号',
      username: '用户名',
      userId: '通行码',
      enterUsername: '输入任意用户名',
      enterUserId: '输入任意通行码',
      saveAndContinue: '保存并继续',
      loadingImage: '正在加载图片...',
      scannedPostcardAlt: '扫描的明信片',
      location: '地点',
      collected: '收藏时间',
      collector: '收藏者',
      uploading: '上传中...',
      uploadPicture: '上传图片',
      collectionMemory: '回忆合集',
      noCollectionMemory: '暂未找到回忆内容。',
      gridTitle: '曾经到访，如今成回忆。',
      noPostcardData: '未找到该账号的明信片数据。',
      fetchError: '获取数据失败，请检查用户名和用户ID。',
      memoryPromptFallback: '你对这个地方的回忆是什么？',
      uploadNeedCredentials: '上传前请先设置用户名和用户ID。',
      uploadFailed: '上传失败。',
      uploadResponseMissing: '上传响应缺少已保存文件列表。',
      uploadingFiles: ({ count }) => `正在上传 ${count} 个文件...`,
      uploadedFiles: ({ count }) => `成功上传 ${count} 个文件。`,
      enterBothCredentials: '请输入用户名和用户ID。',
      imagePreview: '图片预览',
      suggestionPlaceholder: '请输入建议内容',
      sendSuggestion: '发送建议',
      sendingSuggestion: '发送中...',
      suggestionNeedText: '请输入建议内容。',
      suggestionSent: '感谢您的建议',
      suggestionFailed: '暂时无法发送建议。'
    }
  };

  const SUPPORTED_LANGUAGES = [
    { value: 'en', label: 'EN' },
    { value: 'fr', label: 'Français' },
    { value: 'ru', label: 'Русский' },
    { value: 'ko', label: '한국어' },
    { value: 'zh', label: '中文' }
  ];

  let postcardMemories = [];

  let currentYear = new Date().getFullYear();
  let currentMonth = String(new Date().getMonth() + 1).padStart(2, '0');

  let isLoadingPostcard = true;
  let showCredentialsForm = false;
  let credentialsError = '';
  let isUploadingImages = false;
  let uploadStatus = '';
  let uploadInput;
  let uploadImageField = UPLOAD_IMAGE_FIELD;
  let showUploadPictureButton = false;
  let suggestionSenderContact = '';
  let suggestionMessage = '';
  let isSendingSuggestion = false;
  let isEmailJsReady = false;
  let showTourBookingModal = false;
  let tourBookingName = '';
  let tourBookingContact = '';
  let tourBookingDate = '';
  let isSendingTourBooking = false;
  let tourBookingError = '';
  let tourBookingStatus = '';
  let imageFieldPlaceholder = MEMORY_PROMPTS_BY_LANGUAGE.en[0];
  let inputUsername = '';
  let inputUserId = '';
  let lightboxImageSrc = '';
  let currentLanguage = 'en';
  let lightboxImageAlt = 'Image preview';
  let activeUsername = API_USERNAME;
  let activeUserId = API_USER_ID;
  let activeTheme = 'dark';
  let scannedPostcardSrc = MAIN_IMAGE_URL;
  let scannedPostcardDetails = {
    title: 'Garden Home Postcard',
    subtitle: 'Front Gate in Spring',
    location: 'Portland, Oregon',
    collected: '2026-02-28',
    collector: 'Garden Home Archive',
    collectorUsername: '',
    collectorUserId: ''
  };

  function getLanguageLocale() {
    if (currentLanguage === 'ko') return 'ko-KR';
    if (currentLanguage === 'zh') return 'zh-CN';
    if (currentLanguage === 'fr') return 'fr-FR';
    if (currentLanguage === 'ru') return 'ru-RU';
    return 'en-US';
  }

  function getMemoryPrompts(languageCode = currentLanguage) {
    return MEMORY_PROMPTS_BY_LANGUAGE[languageCode] || MEMORY_PROMPTS_BY_LANGUAGE.en;
  }

  function t(key, params = {}) {
    const languageTranslations = TRANSLATIONS[currentLanguage] || TRANSLATIONS.en;
    const fallbackTranslations = TRANSLATIONS.en;
    const value = languageTranslations[key] ?? fallbackTranslations[key] ?? key;

    if (typeof value === 'function') {
      return value(params);
    }

    return String(value).replace(/\{(\w+)\}/g, (_, token) => params[token] ?? '');
  }

  function slugify(text) {
    return text
      .toString()
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '-')
      .replace(/[^\w\-]+/g, '')
      .replace(/\-\-+/g, '-')
      .replace(/^-+/, '')
      .replace(/-+$/, '');
  }

  function setLanguage(languageCode, shouldPersist = true) {
    const nextLanguage = SUPPORTED_LANGUAGES.some((language) => language.value === languageCode)
      ? languageCode
      : 'en';

    currentLanguage = nextLanguage;
    imageFieldPlaceholder = getRotatingMemoryPrompt();

    if (lightboxImageSrc) {
      lightboxImageAlt = t('imagePreview');
    }

    if (shouldPersist) {
      safeSetLocalStorageValue(LOCAL_STORAGE_LANGUAGE_KEY, currentLanguage);
    }
  }

  function normalizeCredential(value) {
    return String(value ?? '')
      .trim()
      .toLowerCase();
  }

  function getCollectorName(collectorValue) {
    if (typeof collectorValue === 'string') {
      return collectorValue;
    }

    return collectorValue?.visitorName || collectorValue?.name || collectorValue?.username || '';
  }

  function getCollectorUsername(collectorValue) {
    if (typeof collectorValue === 'string') {
      return collectorValue;
    }

    return collectorValue?.username || collectorValue?.visitorName || collectorValue?.name || '';
  }

  function getCollectorUserId(collectorValue) {
    if (typeof collectorValue === 'string') {
      return '';
    }

    return collectorValue?.userID || collectorValue?.userId || collectorValue?.id || '';
  }

  function isCollectorAccountMatch() {
    const currentUsername = normalizeCredential(activeUsername);
    const currentUserId = normalizeCredential(activeUserId);
    const collectorUsername = normalizeCredential(scannedPostcardDetails.collectorUsername);
    const collectorUserId = normalizeCredential(scannedPostcardDetails.collectorUserId);

    return Boolean(
      currentUsername &&
        currentUserId &&
        collectorUsername &&
        collectorUserId &&
        currentUsername === collectorUsername &&
        currentUserId === collectorUserId
    );
  }

  function applyTheme(themeName, shouldPersist = true) {
    activeTheme = themeName === 'light' ? 'light' : 'dark';

    if (typeof document !== 'undefined') {
      document.body.dataset.theme = activeTheme;
    }

    if (shouldPersist) {
      safeSetLocalStorageValue(LOCAL_STORAGE_THEME_KEY, activeTheme);
    }
  }

  function toggleTheme() {
    applyTheme(activeTheme === 'dark' ? 'light' : 'dark');
  }

  function toPostcardMemory(collection, index = 0) {
    const title =
      collection?.collectionName ||
      collection?.collectionTitle ||
      collection?.title ||
      collection?.name ||
      `Postcard Memory ${index + 1}`;

    const body =
      collection?.collectionDescription ||
      collection?.description ||
      collection?.body ||
      'No memory description available.';

    const uniqueId = collection?.collectionUniqueID || collection?.id || `memory-${index + 1}`;
    const pictureUrl = collection?.collectionPicture;
    const videoUrl = collection?.collectionVideo;
    const collectedDate = collection?.collectionCollected || collection?.collectionTimstamp;
    const placeName = collection?.collectionPlace || collection?.location;
    const provinceName = collection?.collectionProvince;
    const collectorValue = collection?.collectionCollector || collection?.collector;
    const collectorName =
      getCollectorName(collectorValue) ||
      collection?.collectionCollectorName ||
      collection?.collectorName ||
      scannedPostcardDetails.collector;
    const collectorUsername =
      collection?.collectionCollector ||
      collection?.collectionCollectorUsername ||
      getCollectorUsername(collectorValue) ||
      scannedPostcardDetails.collectorUsername;
    const collectorUserId =
      collection?.collectionCollectorID ||
      collection?.collectionCollectorId ||
      getCollectorUserId(collectorValue) ||
      scannedPostcardDetails.collectorUserId;
    const placeWithProvince =
      placeName && provinceName ? `${placeName}, ${provinceName}` : placeName || scannedPostcardDetails.location;

    return {
      ...collection,
      id: uniqueId,
      title,
      body,
      src:
        pictureUrl ||
        POSTCARD_MEMORY_IMAGE_URLS[index] ||
        `https://placehold.co/640x400/png?text=${uniqueId}`,
      video: videoUrl || null,
      placeVisitorLists: collection?.placeVisitorLists || [],
      placeId: collection?.collectionPlaceID || null,
      isCollected: Boolean(collection?.collectionIsCollected),
      collector: collectorName,
      collectorUsername,
      collectorUserId,
      collected: collectedDate || new Date().toISOString().slice(0, 10),
      timestamp: collection?.collectionTimstamp || null,
      location: placeWithProvince
    };
  }

  function toPostcardDetails(memory) {
    const subtitleParts = [];

    if (memory.id) subtitleParts.push(`Collection ${memory.id}`);
    if (memory.placeId) subtitleParts.push(`Place ID ${memory.placeId}`);
    console.log('scannedPostcardDetails:', memory);

    return {
      title: memory.title,
      subtitle: subtitleParts.length ? subtitleParts.join(' · ') : scannedPostcardDetails.subtitle,
      location: memory.location,
      collected: memory.collected,
      collector: memory.collector,
      collectorUsername: memory.collectorUsername,
      collectorUserId: memory.collectorUserId,
      collectionPlaceDirect: memory.collectionPlaceDirectName
    };
  }

  function getCollectionMemoryItems() {
    return postcardMemories.flatMap((collection) => {
      const memoryList = Array.isArray(collection?.collectionMemory) ? collection.collectionMemory : [];

      return memoryList.map((memory, memoryIndex) => ({
        id: memory?.id || `${collection.id}-memory-${memoryIndex + 1}`,
        about: memory?.memoryAbout || `Memory ${memoryIndex + 1}`,
        image: memory?.memoryPicture || '',
        isPrivate: Boolean(memory?.memoryisPrivate),
        timestamp: memory?.memoryTimestamp || ''
      }));
    });
  }

  function extractCollectionsFromApiResponse(data) {
    if (Array.isArray(data)) {
      return data;
    }

    if (data && typeof data === 'object') {
      if (Array.isArray(data.visitorCollections)) {
        return [data, ...data.visitorCollections];
      }

      const nestedArrayKeys = ['collections', 'data', 'results', 'items', 'records', 'rows'];

      for (const key of nestedArrayKeys) {
        if (Array.isArray(data[key])) {
          return data[key];
        }
      }

      const numericKeys = Object.keys(data)
        .filter((key) => /^[0-9]+$/.test(key))
        .sort((a, b) => Number(a) - Number(b));

      if (numericKeys.length && numericKeys.length === Object.keys(data).length) {
        return numericKeys.map((key) => data[key]);
      }
    }

    return [data];
  }

  function getCollectionStrFromUrl() {
    if (typeof window === 'undefined') {
      return DEFAULT_COLLECTION_STR;
    }

    const pathSegments = window.location.pathname
      .split('/')
      .map((segment) => segment.trim())
      .filter(Boolean);

    return pathSegments[pathSegments.length - 1] || DEFAULT_COLLECTION_STR;
  }

  function getPostcardDetailsApiUrl() {
    return `${POSTCARD_DETAILS_API_BASE_URL}${getCollectionStrFromUrl()}/`;
  }

async function fetchLookPlaceData() {
  const headers = {
    'Content-Type': 'application/json'
  };

  if (ACCEPT_HEADER.includes('application/json')) {
    headers['Accept'] = 'application/json';
  }

  const response = await fetch(getPostcardDetailsApiUrl(), {
    method: 'POST',
    headers,
    body: JSON.stringify({
      username: activeUsername,
      userID: activeUserId,
      collectionStr: getCollectionStrFromUrl()
    })
  });

    if (!response.ok) {
      throw new Error(`Failed to fetch postcard details: ${response.status}`);
    }

    const data = await response.json();

    if (data?.error) {
      throw new Error(data.error);
    }

    return data;
  }

  async function getPostcardMemories() {
    const data = await fetchLookPlaceData();
    const collections = extractCollectionsFromApiResponse(data);

    return collections.map((collection, index) => toPostcardMemory(collection, index));
  }

  async function getPostcardDetails() {
    const memories = await getPostcardMemories();
    return memories[0] ? toPostcardDetails(memories[0]) : scannedPostcardDetails;
  }

  function formatCollectedDate(value) {
    if (!value) return '';

    const [year, month, day] = value.split('-').map(Number);
    const locale = getLanguageLocale();

    if (year && month && day) {
      return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString(locale, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        timeZone: 'UTC'
      });
    }

    const parsed = new Date(value);

    if (Number.isNaN(parsed.getTime())) {
      return value;
    }

    return parsed.toLocaleDateString(locale, {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  async function loadPostcardData() {
    isLoadingPostcard = true;
    credentialsError = '';

    await new Promise((resolve) => {
      setTimeout(resolve, LOADING_DELAY_MS);
    });

    try {
      postcardMemories = await getPostcardMemories();
      if (postcardMemories[0]) {
        scannedPostcardDetails = toPostcardDetails(postcardMemories[0]);
        scannedPostcardSrc = postcardMemories[0].src || MAIN_IMAGE_URL;
      } else {
        credentialsError = t('noPostcardData');
        showCredentialsForm = true;
      }
    } catch (error) {
      console.error(error);
      credentialsError = t('fetchError');
      showCredentialsForm = true;
    } finally {
      isLoadingPostcard = false;
    }
  }

  function safeGetLocalStorageValue(key) {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.error('Unable to read localStorage key:', key, error);
      return null;
    }
  }

  function safeSetLocalStorageValue(key, value) {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch (error) {
      console.error('Unable to write localStorage key:', key, error);
      return false;
    }
  }

  function safeRemoveLocalStorageValue(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.error('Unable to remove localStorage key:', key, error);
      return false;
    }
  }

  function persistSession(user, userID, token = null) {
    const isGuest = user === 'guestuser' && userID === 'guestuser';

    safeSetLocalStorageValue(LOCAL_STORAGE_SESSION_USER_KEY, user);
    safeSetLocalStorageValue(LOCAL_STORAGE_SESSION_USER_ID_KEY, userID);

    if (token !== null && token !== undefined) {
      safeSetLocalStorageValue(LOCAL_STORAGE_SESSION_TOKEN_KEY, token);
    } else {
      safeRemoveLocalStorageValue(LOCAL_STORAGE_SESSION_TOKEN_KEY);
    }

    setSession({ user, userID, token, isGuest });
  }

  function openCreateAccountForm() {
    credentialsError = '';
    inputUsername = '';
    inputUserId = '';
    showCredentialsForm = true;
  }

  function getRotatingMemoryPrompt() {
    const memoryPrompts = getMemoryPrompts();

    if (!memoryPrompts.length) {
      return t('memoryPromptFallback');
    }

    const previousPromptIndex = Number.parseInt(
      safeGetLocalStorageValue(MEMORY_PROMPT_STORAGE_KEY) ?? '',
      10
    );

    let nextPromptIndex = Math.floor(Math.random() * memoryPrompts.length);

    if (
      memoryPrompts.length > 1 &&
      Number.isInteger(previousPromptIndex) &&
      previousPromptIndex >= 0 &&
      previousPromptIndex < memoryPrompts.length &&
      nextPromptIndex === previousPromptIndex
    ) {
      nextPromptIndex = (nextPromptIndex + 1) % memoryPrompts.length;
    }

    safeSetLocalStorageValue(MEMORY_PROMPT_STORAGE_KEY, String(nextPromptIndex));
    return memoryPrompts[nextPromptIndex];
  }

  async function uploadImages(files) {
    const formData = new FormData();

    for (const file of files) {
      formData.append('images', file);
    }

    formData.append('imageField', uploadImageField.trim());
    formData.append('username', activeUsername);
    formData.append('userID', activeUserId);
    formData.append('collectionUniqueID', getCollectionStrFromUrl());

    const response = await fetch(UPLOAD_API_URL, {
      method: 'POST',
      body: formData
    });

    let responseBody = null;

    try {
      responseBody = await response.json();
    } catch {
      responseBody = null;
    }

    if (!response.ok) {
      const errorMessage =
        responseBody?.error || responseBody?.message || `Upload failed with status ${response.status}`;
      throw new Error(errorMessage);
    }

    if (!Array.isArray(responseBody?.saved)) {
      throw new Error(t('uploadResponseMissing'));
    }

    return responseBody.saved;
  }

  function getUploadedImageUrl(savedItem, fallbackFile) {
    if (typeof savedItem === 'string') {
      return savedItem;
    }

    return (
      savedItem?.memoryPicture ||
      savedItem?.image ||
      savedItem?.imageUrl ||
      savedItem?.url ||
      savedItem?.src ||
      savedItem?.path ||
      fallbackFile?.previewUrl ||
      ''
    );
  }

  function appendUploadedItemsToCollectionMemory(savedItems, uploadedFiles) {
    const nowIso = new Date().toISOString();

    const newMemoryItems = savedItems
      .map((savedItem, index) => {
        const fallbackFile = uploadedFiles[index];
        const imageUrl = getUploadedImageUrl(savedItem, fallbackFile);

        if (!imageUrl) {
          return null;
        }

        const memoryAbout =
          (typeof savedItem === 'object' && savedItem?.memoryAbout) ||
          uploadImageField.trim() ||
          fallbackFile?.name ||
          `Uploaded memory ${index + 1}`;

        return {
          id:
            (typeof savedItem === 'object' && (savedItem?.id || savedItem?.memoryID)) ||
            `uploaded-memory-${Date.now()}-${index + 1}`,
          memoryAbout,
          memoryPicture: imageUrl,
          memoryisPrivate: false,
          memoryTimestamp:
            (typeof savedItem === 'object' && (savedItem?.memoryTimestamp || savedItem?.timestamp)) || nowIso
        };
      })
      .filter(Boolean);

    if (!newMemoryItems.length) {
      return;
    }

    if (!postcardMemories.length) {
      postcardMemories = [
        {
          id: getCollectionStrFromUrl(),
          title: scannedPostcardDetails.title,
          body: scannedPostcardDetails.subtitle,
          src: scannedPostcardSrc,
          collector: scannedPostcardDetails.collector,
          collectorUsername: scannedPostcardDetails.collectorUsername,
          collectorUserId: scannedPostcardDetails.collectorUserId,
          collected: scannedPostcardDetails.collected,
          location: scannedPostcardDetails.location,
          collectionMemory: newMemoryItems
        }
      ];
      return;
    }

    const [firstCollection, ...remainingCollections] = postcardMemories;
    const existingMemory = Array.isArray(firstCollection?.collectionMemory)
      ? firstCollection.collectionMemory
      : [];

    postcardMemories = [
      {
        ...firstCollection,
        collectionMemory: [...newMemoryItems, ...existingMemory]
      },
      ...remainingCollections
    ];
  }

  function openUploadPicker() {
    uploadInput?.click();
  }

  function handleImageFieldInput(event) {
    uploadImageField = event.currentTarget?.value || '';
    showUploadPictureButton = uploadImageField.trim().length > 0;
  }

  async function handleUploadSelection(event) {
    const files = Array.from(event.currentTarget?.files || []);

    if (!files.length) {
      return;
    }

    if (!activeUsername || !activeUserId) {
      uploadStatus = t('uploadNeedCredentials');
      event.currentTarget.value = '';
      return;
    }

    isUploadingImages = true;
    uploadStatus = t('uploadingFiles', { count: files.length });

    try {
      const saved = await uploadImages(files);
      appendUploadedItemsToCollectionMemory(saved, files);
      uploadStatus = t('uploadedFiles', { count: saved.length });
      uploadImageField = '';
      showUploadPictureButton = false;
      imageFieldPlaceholder = getRotatingMemoryPrompt();
    } catch (error) {
      console.error('Upload failed:', error);
      uploadStatus = error?.message || t('uploadFailed');
    }

    isUploadingImages = false;
    event.currentTarget.value = '';
  }

  function openTourBookingModal() {
    tourBookingError = '';
    tourBookingName =
      safeGetLocalStorageValue(LOCAL_STORAGE_TOUR_NAME_KEY)?.trim() || activeUsername || tourBookingName;
    tourBookingContact =
      safeGetLocalStorageValue(LOCAL_STORAGE_CONTACT_KEY)?.trim() ||
      suggestionSenderContact ||
      tourBookingContact;
    tourBookingDate = safeGetLocalStorageValue(LOCAL_STORAGE_TOUR_DATE_KEY)?.trim() || tourBookingDate;
    showTourBookingModal = true;
  }

  function closeTourBookingModal() {
    showTourBookingModal = false;
    tourBookingError = '';
  }

  async function submitTourBooking() {
    const normalizedName = tourBookingName.trim();
    const normalizedContact = tourBookingContact.trim();
    const normalizedDate = tourBookingDate.trim();

    if (!normalizedName) {
      tourBookingError = t('bookingNeedName');
      return;
    }

    if (!normalizedContact) {
      tourBookingError = t('bookingNeedContact');
      return;
    }

    if (!normalizedDate) {
      tourBookingError = t('bookingNeedDate');
      return;
    }

    if (!window.emailjs || !isEmailJsReady) {
      tourBookingError = t('suggestionFailed');
      return;
    }

    tourBookingName = normalizedName;
    tourBookingContact = normalizedContact;
    tourBookingDate = normalizedDate;
    suggestionSenderContact = normalizedContact;
    safeSetLocalStorageValue(LOCAL_STORAGE_TOUR_NAME_KEY, normalizedName);
    safeSetLocalStorageValue(LOCAL_STORAGE_CONTACT_KEY, normalizedContact);
    safeSetLocalStorageValue(LOCAL_STORAGE_TOUR_DATE_KEY, normalizedDate);

    const bookingMessage = [
      'Island tour booking',
      `name: ${normalizedName}`,
      `contact: ${normalizedContact}`,
      `date: ${normalizedDate}`,
      `place: ${scannedPostcardDetails.title}`
    ].join(' | ');

    isSendingTourBooking = true;
    tourBookingError = '';

    try {
      await window.emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, {
        to_name: EMAILJS_TO_NAME,
        from_name: normalizedName,
        sender_contact: normalizedContact,
        reply_to: EMAILJS_REPLY_TO,
        guest_contact: 'none',
        resort_id: activeUsername || normalizedName,
        message: bookingMessage
      });

      tourBookingStatus = t('bookingSaved');
      closeTourBookingModal();
    } catch (error) {
      console.error('Tour booking email failed:', error);
      tourBookingError = t('suggestionFailed');
    } finally {
      isSendingTourBooking = false;
    }
  }

  function handleWindowKeydown(event) {
    if (event.key === 'Escape' && showTourBookingModal) {
      closeTourBookingModal();
    }
  }

  async function submitCredentials() {
    const normalizedUsername = inputUsername.trim();
    const normalizedUserId = inputUserId.trim();

    if (!normalizedUsername || !normalizedUserId) {
      credentialsError = t('enterBothCredentials');
      return;
    }

    activeUsername = normalizedUsername;
    activeUserId = normalizedUserId;
    safeSetLocalStorageValue(LOCAL_STORAGE_USERNAME_KEY, normalizedUsername);
    safeSetLocalStorageValue(LOCAL_STORAGE_USER_ID_KEY, normalizedUserId);
    persistSession(normalizedUsername, normalizedUserId, null);
    showCredentialsForm = false;

    await loadPostcardData();
  }

  function openImagePreview(src, alt = t('imagePreview')) {
    if (!src) {
      return;
    }

    lightboxImageSrc = src;
    lightboxImageAlt = alt;
  }

  function closeImagePreview() {
    lightboxImageSrc = '';
    lightboxImageAlt = t('imagePreview');
  }

  function getSuggestionLastSentKey(username) {
    const normalizedUsername = normalizeCredential(username);
    return `${SUGGESTION_LAST_SENT_KEY_PREFIX}:${normalizedUsername || 'guest'}`;
  }

  function getSuggestionCooldownMessage(msRemaining) {
    const totalMinutes = Math.ceil(msRemaining / 60000);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours > 0) {
      return `You can send another suggestion in ${hours}h ${minutes}m.`;
    }

    return `You can send another suggestion in ${minutes}m.`;
  }

  async function sendSuggestion() {
    const guestMessage = suggestionMessage.trim();
    let senderContact = suggestionSenderContact.trim();

    if (!guestMessage) {
      alert(t('suggestionNeedText'));
      return;
    }

    if (!window.emailjs || !isEmailJsReady) {
      alert(t('suggestionFailed'));
      return;
    }

    const existingUsername = activeUsername?.trim();

    if (!existingUsername) {
      const promptedUsername = window.prompt('Please your name');

      if (!promptedUsername?.trim()) {
        return;
      }

      activeUsername = promptedUsername.trim();
      safeSetLocalStorageValue(LOCAL_STORAGE_USERNAME_KEY, activeUsername);
      alert('Username saved. Click Send again.');
      return;
    }

    if (!senderContact) {
      const promptedContact = window.prompt('Your contact');

      if (!promptedContact?.trim()) {
        return;
      }

      suggestionSenderContact = promptedContact.trim();
      senderContact = suggestionSenderContact;
      safeSetLocalStorageValue(LOCAL_STORAGE_CONTACT_KEY, suggestionSenderContact);
      alert('Contact saved. Sending now...');
    }

    const suggestionLastSentKey = getSuggestionLastSentKey(activeUsername);
    const lastSentRaw = safeGetLocalStorageValue(suggestionLastSentKey);
    const lastSentAt = Number.parseInt(lastSentRaw || '', 10);

    if (Number.isFinite(lastSentAt)) {
      const msElapsed = Date.now() - lastSentAt;

      if (msElapsed < SUGGESTION_COOLDOWN_MS) {
        alert(getSuggestionCooldownMessage(SUGGESTION_COOLDOWN_MS - msElapsed));
        return;
      }
    }

    isSendingSuggestion = true;
    alert('Sending Message');

    try {
      await window.emailjs.send(EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, {
        to_name: EMAILJS_TO_NAME,
        from_name: activeUsername,
        sender_contact: senderContact,
        reply_to: EMAILJS_REPLY_TO,
        guest_contact: 'none',
        resort_id: activeUsername,
        message: guestMessage
      });

      safeSetLocalStorageValue(suggestionLastSentKey, String(Date.now()));
      suggestionMessage = '';
      alert('Message Sent !');
    } catch (error) {
      console.error('Suggestion email failed:', error);
      alert('Message Not Sent !');
    } finally {
      isSendingSuggestion = false;
    }
  }

  onMount(async () => {
    const initializeEmailJs = () => {
      if (window.emailjs) {
        window.emailjs.init({
          publicKey: EMAILJS_PUBLIC_KEY
        });
        isEmailJsReady = true;
        return;
      }

      setTimeout(initializeEmailJs, 150);
    };

    initializeEmailJs();

    const savedTheme = safeGetLocalStorageValue(LOCAL_STORAGE_THEME_KEY);
    applyTheme(savedTheme === 'light' ? 'light' : 'dark', false);

    const savedLanguage = safeGetLocalStorageValue(LOCAL_STORAGE_LANGUAGE_KEY)?.trim();
    setLanguage(savedLanguage || 'en', false);

    const sessionUser = safeGetLocalStorageValue(LOCAL_STORAGE_SESSION_USER_KEY)?.trim();
    const sessionUserId = safeGetLocalStorageValue(LOCAL_STORAGE_SESSION_USER_ID_KEY)?.trim();
    const sessionToken = safeGetLocalStorageValue(LOCAL_STORAGE_SESSION_TOKEN_KEY)?.trim() || null;
    const savedUsername = safeGetLocalStorageValue(LOCAL_STORAGE_USERNAME_KEY)?.trim();
    const savedUserId = safeGetLocalStorageValue(LOCAL_STORAGE_USER_ID_KEY)?.trim();
    suggestionSenderContact = safeGetLocalStorageValue(LOCAL_STORAGE_CONTACT_KEY)?.trim() || '';
    tourBookingName = safeGetLocalStorageValue(LOCAL_STORAGE_TOUR_NAME_KEY)?.trim() || savedUsername || '';
    tourBookingContact = suggestionSenderContact;
    tourBookingDate = safeGetLocalStorageValue(LOCAL_STORAGE_TOUR_DATE_KEY)?.trim() || '';

    if (sessionUser && sessionUserId) {
      activeUsername = sessionUser;
      activeUserId = sessionUserId;
      persistSession(sessionUser, sessionUserId, sessionToken);
      await loadPostcardData();
      return;
    }

    if (savedUsername && savedUserId) {
      activeUsername = savedUsername;
      activeUserId = savedUserId;
      persistSession(savedUsername, savedUserId, null);
      await loadPostcardData();
      return;
    }

    initializeGuestSession();
    activeUsername = 'guestuser';
    activeUserId = 'guestuser';
    persistSession('guestuser', 'guestuser', null);
    showCredentialsForm = false;

    await loadPostcardData();
  });
</script>

<svelte:head>
  <script defer type="text/javascript" src="https://cdn.jsdelivr.net/npm/@emailjs/browser@4/dist/email.min.js"></script>
</svelte:head>

<svelte:window on:keydown={handleWindowKeydown} />

<div class="page">
  <header class="topbar">
    <div class="brand">{t('brandTitle')}</div>
    <div class="account-chip" aria-live="polite">
      <span>{t('welcome', { name: $session.isGuest ? t('guest') : activeUsername || t('guest') })}</span>
      <div class="lang-switch" role="group" aria-label="Language selector">
        {#each SUPPORTED_LANGUAGES as language}
          <button
            class="lang-btn"
            class:is-active={currentLanguage === language.value}
            type="button"
            on:click={() => setLanguage(language.value)}
            aria-pressed={currentLanguage === language.value}
          >
            {language.label}
          </button>
        {/each}
      </div>
      <button
        class="theme-toggle"
        type="button"
        on:click={toggleTheme}
        aria-label={activeTheme === 'dark' ? t('themeToLight') : t('themeToDark')}
        title={activeTheme === 'dark' ? t('themeToLight') : t('themeToDark')}
      >
        {activeTheme === 'dark' ? '☀️' : '🌙'}
      </button>
      {#if $session.isGuest}
        <button class="cta guest-upgrade-btn" type="button" on:click={openCreateAccountForm}>
          {t('enterAccount')}
        </button>
      {/if}
    </div>
  </header>

  <section class="hero">


    {#if showCredentialsForm}
      <div class="credentials-box" aria-live="polite">
        <h3>{t('enterAccount')}</h3>
        <form class="credentials-form" on:submit|preventDefault={submitCredentials}>
          <label>
            {t('username')}
            <input bind:value={inputUsername} type="text" placeholder={t('enterUsername')} />
          </label>
          <label>
            {t('userId')}
            <input bind:value={inputUserId} type="text" placeholder={t('enterUserId')} />
          </label>
          {#if credentialsError}
            <p class="credentials-error">{credentialsError}</p>
          {/if}
          <button class="cta" type="submit">{t('saveAndContinue')}</button>
        </form>
      </div>
    {:else}
      <div class="postcard-frame" aria-live="polite">
        {#if isLoadingPostcard}
          <div class="loading-state">
            <span class="spinner" aria-hidden="true"></span>
            <span>{t('loadingImage')}</span>
          </div>
        {:else}
          <img id="scanned-postcard" src={scannedPostcardSrc} alt={t('scannedPostcardAlt')} />
          <div class="postcard-meta" id="scanned-postcard-meta">
            <h3>{scannedPostcardDetails.title}</h3>
            <div class="meta-grid">
              <p>{scannedPostcardDetails.location}</p>
              <p>{formatCollectedDate(scannedPostcardDetails.collected)}</p>
              <p>{scannedPostcardDetails.collector}</p>
               <a href={`/places/${scannedPostcardDetails.collectionPlaceDirect}/${currentYear}/${currentMonth}`} class=""><p> See More </p></a>
            </div>  
            
            

            <!--
            <div class="booking-actions">
              <button class="cta tour-booking-btn" type="button" on:click={openTourBookingModal}>
                {t('bookIslandTour')}
              </button>
              {#if tourBookingStatus}
                <p class="tour-booking-status">{tourBookingStatus}</p>
              {/if}
            </div>
            -->
            {#if isCollectorAccountMatch()}
              <div class="hero-actions">

                <input
                  id="modalMultiImageUpload"
                  bind:this={uploadInput}
                  class="upload-input"
                  type="file"
                  name="images"
                  accept="image/*"
                  multiple
                  required
                  on:change={handleUploadSelection}
                />
                <textarea
                  id="modalImageField"
                  bind:value={uploadImageField}
                  class="image-field-input"
                  name="imageField"
                  rows="2"
                  on:input={handleImageFieldInput}
                  placeholder={imageFieldPlaceholder}
                ></textarea>
                                {#if showUploadPictureButton}
                  <button class="cta" type="button" on:click={openUploadPicker} disabled={isUploadingImages}>
                    {isUploadingImages ? t('uploading') : t('uploadPicture')}
                  </button>
                {/if}
              </div>
            {/if}
            {#if isCollectorAccountMatch() && uploadStatus}
              <p class="upload-status">{uploadStatus}</p>
            {/if}
            <!--
            <div class="suggestion-actions">
              <input
                class="suggestion-input"
                type="text"
                bind:value={suggestionMessage}
                placeholder={t('suggestionPlaceholder')}
              />
              <button
                class="cta suggestion-send-btn"
                type="button"
                on:click={sendSuggestion}
                disabled={isSendingSuggestion || !isEmailJsReady}
                aria-label={isSendingSuggestion ? t('sendingSuggestion') : t('sendSuggestion')}
                title={isSendingSuggestion ? t('sendingSuggestion') : t('sendSuggestion')}
              >
                {#if isSendingSuggestion}
                  <svg class="suggestion-sending-icon" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M8 1.5a.75.75 0 0 1 .75.75v1.7a.75.75 0 0 1-1.5 0v-1.7A.75.75 0 0 1 8 1.5Zm0 10.35a.75.75 0 0 1 .75.75v1.65a.75.75 0 0 1-1.5 0V12.6a.75.75 0 0 1 .75-.75ZM2.25 7.25h1.7a.75.75 0 0 1 0 1.5h-1.7a.75.75 0 0 1 0-1.5Zm9.8 0h1.7a.75.75 0 0 1 0 1.5h-1.7a.75.75 0 0 1 0-1.5ZM3.75 3.75a.75.75 0 0 1 1.06 0l1.2 1.2a.75.75 0 1 1-1.06 1.06l-1.2-1.2a.75.75 0 0 1 0-1.06Zm6.24 6.24a.75.75 0 0 1 1.06 0l1.2 1.2a.75.75 0 1 1-1.06 1.06l-1.2-1.2a.75.75 0 0 1 0-1.06ZM3.75 12.25a.75.75 0 0 1 0-1.06l1.2-1.2a.75.75 0 1 1 1.06 1.06l-1.2 1.2a.75.75 0 0 1-1.06 0Zm6.24-6.24a.75.75 0 0 1 0-1.06l1.2-1.2a.75.75 0 1 1 1.06 1.06l-1.2 1.2a.75.75 0 0 1-1.06 0Z" />
                  </svg>
                {:else}
                  <svg class="suggestion-send-icon" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M15.854.146a.5.5 0 0 1 .11.54l-5.819 14.547a.75.75 0 0 1-1.329.124l-3.178-4.995L.643 7.184a.75.75 0 0 1 .124-1.33L15.314.037a.5.5 0 0 1 .54.11ZM6.636 10.07l2.761 4.338L14.13 2.576 6.636 10.07Zm6.787-8.201L1.591 6.602l4.339 2.76 7.494-7.493Z" />
                  </svg>
                {/if}
              </button>
            </div>
            -->
          </div>
        {/if}
      </div>
    {/if}
  </section>

  <section class="collection-memory">


    {#if getCollectionMemoryItems().length}
      <p class="eyebrow">{t('eyebrow')}</p>
    <p class="subtext">
      {t('subtext')}
    </p>    
      <div class="memory-grid">
        {#each getCollectionMemoryItems() as memory}
            {#if memory.image}
              <button
                class="image-trigger"
                type="button"
                on:click={() => openImagePreview(memory.image, memory.about)}
              >
                <img class="memory-image" src={memory.image} alt={memory.about} />
              </button>
            {/if}
        {/each}
      </div>
    {:else}
      <p class="memory-empty">{t('noCollectionMemory')}</p>
    {/if}
  </section>

  <h2 class="grid-title">{t('gridTitle')}</h2>
  <section class="grid">
    {#each postcardMemories as postcard}
      <article class="card">
        <button class="image-trigger" type="button" on:click={() => openImagePreview(postcard.src, postcard.title)}>
          <img class="collection-image" src={postcard.src} alt={postcard.title} />
        </button>
        <h2>{postcard.title}</h2>
        <p>{postcard.body}</p>
        {#if postcard.id}
          <a class="view-collection-link" href={`/${postcard.id}`} aria-label={`View collection ${postcard.title}`}>
            View
          </a>
        {/if}
      </article>
    {/each}
  </section>

  {#if showTourBookingModal}
    <div class="modal-backdrop" role="presentation">
      <div
        class="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-booking-title"
        tabindex="-1"
      >
        <h3 id="tour-booking-title">{t('islandTourTitle')}</h3>
        <p class="modal-copy">{t('islandTourDescription')}</p>
        <form class="tour-booking-form" on:submit|preventDefault={submitTourBooking}>
          <label>
            {t('nameLabel')}
            <input bind:value={tourBookingName} type="text" placeholder={t('enterName')} />
          </label>
          <label>
            {t('dateLabel')}
            <input bind:value={tourBookingDate} type="date" />
          </label>
          <label>
            {t('contactLabel')}
            <input bind:value={tourBookingContact} type="text" placeholder={t('enterContact')} />
          </label>
          {#if tourBookingError}
            <p class="credentials-error">{tourBookingError}</p>
          {/if}
          <div class="tour-booking-actions">
            <button class="ghost" type="button" on:click={closeTourBookingModal}>{t('cancel')}</button>
            <button class="cta" type="submit" disabled={isSendingTourBooking}>
              {isSendingTourBooking ? t('sendingSuggestion') : t('submitBooking')}
            </button>
          </div>
        </form>
      </div>
    </div>
  {/if}

  {#if lightboxImageSrc}
    <button class="image-lightbox" type="button" on:click={closeImagePreview}>
      <div class="lightbox-content">
        <img class="lightbox-image" src={lightboxImageSrc} alt={lightboxImageAlt} />
        {#if lightboxImageAlt}
          <p class="lightbox-caption">{lightboxImageAlt}</p>
        {/if}
      </div>
    </button>
  {/if}
</div>

<style>
  :global(body) {
    margin: 0;
    font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: #0e1117;
    color: #f4f6fb;
  }

  .page {
    max-width: 1080px;
    margin: 0 auto;

  }

  .topbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    justify-content: space-between;
    padding: 0.5rem 0;
  }

  .brand {
    padding:1em;
    font-weight: 800;
    font-size: 1.5rem;
    color: #00a8ff;
    letter-spacing: -0.02em;
    display: inline-block;
    transform-origin: left top;
    transform: perspective(700px) rotateX(8deg);
    text-shadow:
      0 1px 0 rgba(0, 0, 0, 0.28),
      0 2px 0 rgba(0, 0, 0, 0.2),
      0 10px 20px rgba(0, 0, 0, 0.38);
  }

  .account-chip {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    font-size: 0.82rem;
    color: #b3c1d8;
    background: #121825;
    border: 1px solid #252f44;
    border-radius: 999px;
    padding: 0.4rem 0.7rem;
    white-space: nowrap;
  }

  .account-chip span {
    color: #dbe5f7;
  }

  .theme-toggle {
    font: inherit;
    border-radius: 999px;
    border: 1px solid #37445f;
    background: #0b1222;
    color: #f4f6fb;
    width: 2rem;
    height: 2rem;
    padding: 0;
    cursor: pointer;
    font-size: 0.95rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    flex: 0 0 auto;
  }

  .lang-switch {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
  }

  .lang-btn {
    font: inherit;
    border-radius: 999px;
    border: 1px solid #37445f;
    background: #0b1222;
    color: #dbe5f7;
    min-height: 2rem;
    padding: 0.2rem 0.5rem;
    cursor: pointer;
    font-size: 0.72rem;
    line-height: 1;
    font-weight: 600;
  }

  .lang-btn.is-active {
    background: #00a8ff;
    border-color: #00a8ff;
    color: #00121d;
  }

  :global(body[data-theme='light']) {
    background: #eef3fb;
    color: #0f172a;
  }

  :global(body[data-theme='light'] .brand) {
    color: #0077c8;
  }

  :global(body[data-theme='light'] .account-chip) {
    color: #465a7b;
    background: #e1e9f7;
    border-color: #c8d5eb;
  }

  :global(body[data-theme='light'] .account-chip span) {
    color: #1f2f46;
  }

  :global(body[data-theme='light'] .theme-toggle) {
    background: #0f172a;
    border-color: #0f172a;
    color: #f8fafc;
  }

  :global(body[data-theme='light'] .lang-btn) {
    background: #ffffff;
    border-color: #bfd0e8;
    color: #334155;
  }

  :global(body[data-theme='light'] .lang-btn.is-active) {
    background: #0077c8;
    border-color: #0077c8;
    color: #ffffff;
  }

  :global(body[data-theme='light'] .eyebrow) {
    color: #5b6f93;
    
  }

  :global(body[data-theme='light'] .subtext) {
    color: #334155;
    
  }

  :global(body[data-theme='light'] .postcard-frame),
  :global(body[data-theme='light'] .card) {
    background: #ffffff;
    border-color: #d3deef;
  }

  :global(body[data-theme='light'] .postcard-meta) {
    background: #f5f8ff;
    border-top-color: #d3deef;
  }

  :global(body[data-theme='light'] .meta-grid p),
  :global(body[data-theme='light'] .memory-card h3),
  :global(body[data-theme='light'] h2),
  :global(body[data-theme='light'] .postcard-meta h3) {
    color: #1f2937;
  }

  :global(body[data-theme='light'] .meta-grid span),
  :global(body[data-theme='light'] .subtitle),
  :global(body[data-theme='light'] .memory-card p),
  :global(body[data-theme='light'] .memory-empty),
  :global(body[data-theme='light'] .upload-status),
  :global(body[data-theme='light'] .credentials-form label),
  :global(body[data-theme='light'] .tour-booking-form label),
  :global(body[data-theme='light'] .modal-copy) {
    color: #5b6b88;
  }

  :global(body[data-theme='light'] .ghost) {
    color: #1f2f46;
    border-color: #b8c7df;
  }

  :global(body[data-theme='light'] .image-field-input),
  :global(body[data-theme='light'] .suggestion-input),
  :global(body[data-theme='light'] .credentials-form input),
  :global(body[data-theme='light'] .tour-booking-form input) {
    color: #1f2937;
    background: #ffffff;
    border-color: #bfd0e8;
  }

  :global(body[data-theme='light'] .tour-booking-status) {
    color: #0f6fb5;
  }

  :global(body[data-theme='light'] .modal-card) {
    background: #ffffff;
    border-color: #d3deef;
  }

  :global(body[data-theme='light'] .modal-card h3) {
    color: #1f2937;
  }

  :global(body[data-theme='light'] .image-field-input) {
    background-image:
      linear-gradient(
        110deg,
        rgba(255, 255, 255, 0) 0%,
        rgba(15, 23, 42, 0.05) 45%,
        rgba(15, 23, 42, 0.14) 50%,
        rgba(15, 23, 42, 0.05) 55%,
        rgba(255, 255, 255, 0) 100%
      ),
      linear-gradient(#ffffff, #ffffff);
  }

  :global(body[data-theme='light'] .suggestion-input) {
    background-image:
      linear-gradient(
        110deg,
        rgba(255, 255, 255, 0) 0%,
        rgba(15, 23, 42, 0.05) 45%,
        rgba(15, 23, 42, 0.14) 50%,
        rgba(15, 23, 42, 0.05) 55%,
        rgba(255, 255, 255, 0) 100%
      ),
      linear-gradient(#ffffff, #ffffff);
  }

  .cta,
  .ghost {
    font: inherit;
    border: none;
    border-radius: 999px;
    padding: 0.6rem 1rem;
    cursor: pointer;
  }

  .cta {
    background: #00a8ff;
    color: #00121d;
    font-weight: 700;
  }

  .ghost {
    background: transparent;
    color: #dbe5f7;
    border: 1px solid #37445f;
  }

  .hero {
    padding: 3.5rem 1em 2rem;
    
    max-width: 700px;
  }

  .eyebrow {
    margin: 0;
    color: #8ea0bf;
    letter-spacing: 0.08em;
    font-size: 0.75rem;
    font-weight: 700;
    padding-left: 1em;
  }

  .subtext {
    margin: 0;
    max-width: 60ch;
    color: #dbe5f7;
    font-size: 1.05rem;
    line-height: 1.55;
    font-weight: 500;
    padding-left: 1em;
  }

  .hero-actions {
    margin-top: 1.25rem;
    display: flex;
    gap: 0.65rem;
    flex-wrap: wrap;
    
  }

  .booking-actions {
    margin-top: 1rem;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.45rem;
  }

  .tour-booking-btn {
    min-height: 2.5rem;
  }

  .tour-booking-status {
    margin: 0;
    color: #8ed0ff;
    font-size: 0.9rem;
    line-height: 1.45;
  }

  .suggestion-actions {
    margin-top: 0.85rem;
    display: flex;
    gap: 0.65rem;
    flex-wrap: wrap;
  }

  .suggestion-actions .cta {
    flex: 0 0 auto;
  }

  .suggestion-send-btn {
    width: 2.35rem;
    min-height: 2.35rem;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .suggestion-send-icon,
  .suggestion-sending-icon {
    width: 1rem;
    height: 1rem;
    fill: #00121d;
    display: block;
  }

  .suggestion-sending-icon {
    animation: spin 0.9s linear infinite;
  }

  .suggestion-input {
    font: inherit;
    color: #f4f6fb;
    background: #121825;
    border: 1px solid #37445f;
    border-radius: 999px;
    padding: 0.55rem 0.8rem;
    min-height: 2.35rem;
    flex: 1 1 240px;
    box-sizing: border-box;
    background-image:
      linear-gradient(
        110deg,
        rgba(255, 255, 255, 0) 0%,
        rgba(255, 255, 255, 0.07) 45%,
        rgba(255, 255, 255, 0.18) 50%,
        rgba(255, 255, 255, 0.07) 55%,
        rgba(255, 255, 255, 0) 100%
      ),
      linear-gradient(#121825, #121825);
    background-repeat: no-repeat;
    background-size: 220% 100%, 100% 100%;
    background-position: 140% 0, 0 0;
    animation: inputSweep 2.6s linear infinite;
  }

  .upload-input {
    display: none;
  }

  .upload-status {
    margin: 0.65rem 0 0;
    color: #b3c1d8;
    font-size: 0.9rem;
  }

  .image-field-input {
    font: inherit;
    color: #f4f6fb;
    background: #121825;
    border: 1px solid #37445f;
    border-radius: 0.35rem;
    padding: 0.8rem 1rem;
    width: min(100%, 640px);
    min-height: 4rem;
    height: auto;
    line-height: 1.4;
    flex: 1 1 100%;
    box-sizing: border-box;
    resize: vertical;
    overflow: auto;
    background-image:
      linear-gradient(
        110deg,
        rgba(255, 255, 255, 0) 0%,
        rgba(255, 255, 255, 0.07) 45%,
        rgba(255, 255, 255, 0.18) 50%,
        rgba(255, 255, 255, 0.07) 55%,
        rgba(255, 255, 255, 0) 100%
      ),
      linear-gradient(#121825, #121825);
    background-repeat: no-repeat;
    background-size: 220% 100%, 100% 100%;
    background-position: 140% 0, 0 0;
    animation: inputSweep 2.6s linear infinite;
  }

  .image-field-input:focus,
  .image-field-input:not(:placeholder-shown) {
    animation: none;
    background-position: 0 0, 0 0;
  }

  .suggestion-input:focus,
  .suggestion-input:not(:placeholder-shown) {
    animation: none;
    background-position: 0 0, 0 0;
  }

  .credentials-box {
    margin-top: 1rem;
    
    border-radius: 0;
    border: none;
    background: none;
    
  }

  .credentials-box h3 {
    margin: 0;
    font-size: 1.05rem;
  }

  .credentials-form {
    margin-top: 0.9rem;
    display: grid;
    gap: 0.7rem;
  }

  .credentials-form label {
    display: grid;
    gap: 0.35rem;
    font-size: 0.86rem;
    color: #b3c1d8;
  }

  .credentials-form input {
    font: inherit;
    color: #f4f6fb;
    background: #121825;
    border: 1px solid #37445f;
    border-radius: 0.55rem;
    padding: 0.55rem 0.65rem;
  }

  .credentials-error {
    margin: 0;
    color: #ff9f9f;
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    background: rgba(6, 10, 18, 0.72);
    backdrop-filter: blur(10px);
  }

  .modal-card {
    width: min(100%, 420px);
    box-sizing: border-box;
    border-radius: 1rem;
    border: 1px solid #252f44;
    background: #121825;
    padding: 1rem;
    box-shadow: 0 24px 70px rgba(0, 0, 0, 0.42);
  }

  .modal-card h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #f4f6fb;
  }

  .modal-copy {
    margin: 0.55rem 0 0;
    color: #b3c1d8;
    font-size: 0.95rem;
    line-height: 1.5;
  }

  .tour-booking-form {
    margin-top: 0.95rem;
    display: grid;
    gap: 0.8rem;
  }

  .tour-booking-form label {
    display: grid;
    gap: 0.45rem;
    color: #b3c1d8;
    font-size: 0.9rem;
    font-weight: 600;
  }

  .tour-booking-form input {
    font: inherit;
    color: #f4f6fb;
    background: #0b1222;
    border: 1px solid #37445f;
    border-radius: 0.85rem;
    padding: 0.75rem 0.8rem;
    box-sizing: border-box;
  }

  .tour-booking-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.65rem;
    flex-wrap: wrap;
  }

  .postcard-frame {
    margin-top: 1rem;
    width: min(100%, 640px);
    min-height: 180px;

    overflow: hidden;
  }

  .loading-state {
    min-height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    color: #b3c1d8;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border-radius: 999px;
    border: 2px solid #3e4c68;
    border-top-color: #00a8ff;
    animation: spin 0.8s linear infinite;
  }

  #scanned-postcard {
    display: block;
    width: 100%;
    height: auto;
    max-height: 80vh;
    object-fit: cover;
  }

  .postcard-meta {
    padding: 0.85rem 0.9rem 1rem;
  }

  .postcard-meta h3 {
    margin: 0;
    font-size: 1.05rem;
  }

  .subtitle {
    margin: 0.2rem 0 0.75rem;
    color: #a9bbd8;
    font-size: 0.92rem;
  }

  .meta-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 0.55rem;
  }

  .meta-grid p {
    margin: 0;
    font-size: 0.88rem;
    color: #dbe5f7;
  }

  .meta-grid span {
    display: block;
    margin-bottom: 0.15rem;
    color: #8ea0bf;
    font-size: 0.74rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes inputSweep {
    from {
      background-position: 140% 0, 0 0;
    }

    to {
      background-position: -120% 0, 0 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .image-field-input,
    .suggestion-input {
      animation: none;
      background-position: 0 0, 0 0;
    }
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
  }

  .grid-title {
    margin: 0 0 0.75rem;
    font-size: 1.2rem;
  }

  .collection-memory {
    margin: 0.5rem 0 1.2rem;
  }

  .collection-memory h2 {
    margin: 0 0 0.75rem;
    font-size: 1.2rem;
  }

  .memory-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0;
  }

  .memory-card {
    border: none;
    border-radius: 0;
    margin: 0;
  }

  .memory-image {
    display: block;
    width: 100%;
    height: 120px;
    border-radius: 0;
    object-fit: cover;
    border: none;
  }

  .memory-card h3 {
    margin: 0.4rem 0 0;
    font-size: 0.95rem;
  }

  .memory-meta,
  .memory-card p {
    display: none;
  }

  .memory-empty {
    margin: 0;
    color: #b3c1d8;
    font-size: 0.92rem;
  }

  .card {
    background: #171d29;
    border-radius: 0;
    padding: 0.75rem;
  }

  .collection-image {
    display: block;
    width: 100%;
    height: 128px;
    border-radius: 0.65rem;
    object-fit: cover;
    border: 1px solid #294362;
  }

  .view-collection-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: max-content;
    margin-top: 0.9rem;
    padding: 0.55rem 0.85rem;
    border-radius: 0.75rem;
    border: 1px solid rgba(0, 168, 255, 0.45);
    background: rgba(0, 168, 255, 0.12);
    color: #8ed8ff;
    font-size: 0.95rem;
    font-weight: 700;
    text-decoration: none;
    transition: background 180ms ease, border-color 180ms ease, color 180ms ease, transform 180ms ease;
  }

  .view-collection-link:hover,
  .view-collection-link:focus-visible {
    background: rgba(0, 168, 255, 0.2);
    border-color: rgba(0, 168, 255, 0.75);
    color: #def6ff;
    transform: translateY(-1px);
  }

  .image-trigger {
    border: none;
    background: transparent;
    padding: 0;
    margin: 0;
    width: 100%;
    cursor: zoom-in;
  }

  .image-lightbox {
    position: fixed;
    inset: 0;
    z-index: 999;
    background: rgba(7, 10, 15, 0.92);
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    margin: 0;
    cursor: zoom-out;
  }

  .lightbox-content {
    display: grid;
    gap: 0.75rem;
    max-width: min(96vw, 1400px);
    width: 100%;
    justify-items: center;
  }

  .lightbox-image {
    max-width: 100%;
    max-height: 82vh;
    width: auto;
    height: auto;
    object-fit: contain;
    border-radius: 0.65rem;
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45);
  }

  .lightbox-caption {
    margin: 0;
    color: #f4f6fb;
    font-size: 0.95rem;
    text-align: center;
    max-width: 90vw;
    line-height: 1.4;
    text-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
  }

  h2 {
    margin: 0.7rem 0 0.2rem;
    font-size: 1rem;
  }

  @media (max-width: 680px) {


    .brand {
      font-size: 1.22rem;
      width: 100%;
    }

    .hero {
      padding: 3.5rem 1em 2rem;
    }

    .subtext {
      font-size: 0.98rem;
      line-height: 1.5;
    }

    .account-chip {
      width: 100%;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.5rem;
      white-space: normal;
      order: 2;
      border-radius: 0;
      padding: 0.5rem 0.65rem;
    }

    .account-chip span {
      flex: 1 1 auto;
      min-width: 0;
      overflow-wrap: anywhere;
    }

    .theme-toggle {
      width: 2.2rem;
      height: 2.2rem;
      font-size: 1rem;
    }

    .lang-switch {
      flex: 1 1 auto;
      justify-content: flex-end;
      flex-wrap: wrap;
    }

    .lang-btn {
      min-height: 2.15rem;
      padding: 0.3rem 0.55rem;
      font-size: 0.7rem;
    }

    .postcard-frame {
      width: 100%;
    }

    .credentials-box {
      width: 100%;
      border-radius: 0;
    }

    .postcard-meta {
      padding: 0.8rem;
    }

    .meta-grid {
      grid-template-columns: 1fr;
      gap: 0.6rem;
    }

    .hero-actions {
      margin-top: 1rem;
      gap: 0.55rem;
    }

    .hero-actions .cta,
    .hero-actions .ghost,
    .suggestion-actions .cta,
    .tour-booking-btn,
    .suggestion-input,
    .image-field-input,
    .tour-booking-form input,
    .tour-booking-actions .cta,
    .tour-booking-actions .ghost {
      width: 100%;
      min-height: 46px;
    }

    .tour-booking-actions {
      width: 100%;
    }

    .modal-card {
      padding: 0.9rem;
      border-radius: 0.85rem;
    }

    .suggestion-actions .suggestion-send-btn {
      width: 46px;
      min-height: 46px;
      padding: 0;
    }

    .credentials-form input,
    .cta,
    .ghost {
      min-height: 46px;
    }

    .credentials-form label {
      font-size: 0.9rem;
      gap: 0.4rem;
    }

    .credentials-form input,
    .suggestion-input,
    .image-field-input {
      font-size: 16px;
      padding: 0.72rem 0.72rem;
    }

    .credentials-error {
      font-size: 0.95rem;
      line-height: 1.45;
    }

    .grid {
      grid-template-columns: 1fr;
      gap: 0;
    }

    .memory-grid {
      grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
      gap: 0;
    }

    .collection-image,
    .memory-image {
      height: 80px;
    }

    .topbar {
      flex-wrap: wrap;
      align-items: flex-start;
      gap: 0.65rem;
    }

  }

  @media (max-width: 420px) {


    .brand {
      font-size: 1.12rem;
    }

    .eyebrow {
      font-size: 0.68rem;
      letter-spacing: 0.06em;
    }

    .subtext { 
      font-size: 0.94rem;
    }

    .hero {
      padding: 3.5rem 1em 2rem;
    }

    .postcard-frame,
    .card,
    .memory-card {
    }

    .credentials-box {
      border-radius: 0;
      padding: 0;
    }

    .credentials-box h3 {
      font-size: 1rem;
    }

    .postcard-meta h3,
    .collection-memory h2,
    .grid-title {
      font-size: 1rem;
    }

    .meta-grid p,
    .memory-card p {
      font-size: 0.86rem;
    }

    .cta,
    .ghost {
      font-size: 1rem;
      padding: 0.62rem 0.95rem;
    }
  }

  @media (max-width: 360px) {
    .brand {
      font-size: 1.03rem;
    }

    .account-chip {
      font-size: 0.78rem;
      padding: 0.45rem 0.55rem;
    }

    .theme-toggle {
      width: 2.05rem;
      height: 2.05rem;
    }

    .lang-btn {
      font-size: 0.66rem;
      padding: 0.28rem 0.5rem;
    }

    .subtext {
      font-size: 0.9rem;
    }

    .collection-image,
    .memory-image {
      height: 80px;
    }
  }
</style>