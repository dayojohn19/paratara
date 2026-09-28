<script>
  import GardenHeadLogo from '$lib/assets/gardenhead.png';
  import GardenBodyLogo from '$lib/assets/gardenbody.png';
  import GardenBorderLogo from '$lib/assets/gardenborder.png';
  import { onMount, tick } from 'svelte';
  import { session, setSession, initializeGuestSession } from './stores/session.js';
  import markdownConfig from '../JAVASCRIPT_FUNCTIONS_AND_APIS.md?raw';

  function getMarkdownValue(key, fallbackValue) {
    const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = markdownConfig.match(new RegExp(`^${escapedKey}:[ \\t]*(.*)$`, 'm'));
    return match?.[1]?.trim() || fallbackValue;
  }

  function normalizeLookApiBaseUrl(urlValue) {
    const normalizedUrl = String(urlValue ?? '').trim().replace(/\/+$/, '');
    if (!normalizedUrl) return '';
    const segments = normalizedUrl.split('/');
    const secondLastSegment = segments[segments.length - 2];
    if (secondLastSegment === 'look') segments.pop();
    return `${segments.join('/')}/`;
  }

  function extractDefaultCollectionStr(urlValue, fallbackValue = '11111') {
    const normalizedUrl = String(urlValue ?? '').trim().replace(/\/+$/, '');
    if (!normalizedUrl) return fallbackValue;
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
  const VISITOR_API_URL = getMarkdownValue('VISITOR_API_URL', '/garden/visitor/');
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
  const LOCAL_STORAGE_USERNAME_KEY = getMarkdownValue('LOCAL_STORAGE_USERNAME_KEY', 'postcard_username');
  const LOCAL_STORAGE_USER_ID_KEY = getMarkdownValue('LOCAL_STORAGE_USER_ID_KEY', 'postcard_user_id');
  const LOCAL_STORAGE_SESSION_USER_KEY = getMarkdownValue('LOCAL_STORAGE_SESSION_USER_KEY', 'user');
  const LOCAL_STORAGE_SESSION_USER_ID_KEY = getMarkdownValue('LOCAL_STORAGE_SESSION_USER_ID_KEY', 'userID');
  const LOCAL_STORAGE_SESSION_TOKEN_KEY = getMarkdownValue('LOCAL_STORAGE_SESSION_TOKEN_KEY', 'token');
  const LOCAL_STORAGE_CONTACT_KEY = getMarkdownValue('LOCAL_STORAGE_CONTACT_KEY', 'postcard_contact');
  const LOCAL_STORAGE_TOUR_NAME_KEY = getMarkdownValue('LOCAL_STORAGE_TOUR_NAME_KEY', 'postcard_tour_name');
  const LOCAL_STORAGE_TOUR_DATE_KEY = getMarkdownValue('LOCAL_STORAGE_TOUR_DATE_KEY', 'postcard_tour_date');
  const LOCAL_STORAGE_THEME_KEY = getMarkdownValue('LOCAL_STORAGE_THEME_KEY', 'postcard_theme');
  const LOCAL_STORAGE_LANGUAGE_KEY = getMarkdownValue('LOCAL_STORAGE_LANGUAGE_KEY', 'postcard_language');
  const POSTCARD_DETAILS_API_BASE_URL = normalizeLookApiBaseUrl(API_BASE_URL);
  const DEFAULT_COLLECTION_STR = extractDefaultCollectionStr(API_BASE_URL, '11111');
  let activePostcardTarget = DEFAULT_COLLECTION_STR;

  if (typeof window !== 'undefined') {
    const pathSegments = window.location.pathname
      .split('/')
      .map((segment) => segment.trim())
      .filter(Boolean);
    const lastPathSegment = pathSegments[pathSegments.length - 1];
    if (lastPathSegment && lastPathSegment !== 'garden-memories') {
      activePostcardTarget = lastPathSegment;
    }
  }

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
      bookingSaved: 'Tour request saved. We will contact you soon.',
      // new keys
      mapLabel: 'Map',
      detailsLabel: 'Details',
      learnMore: 'Learn more',
      photoMemoriesTitle: 'Photo memories',
      photoMemoriesDesc: 'Moments uploaded to this postcard.',
      noPhotosTitle: 'No photos yet',
      noPhotosDesc: 'Sign in as the collector to add a memory and upload photos.',
      noRelatedTitle: 'No related postcards',
      noRelatedDesc: 'Related postcards will appear here once this account loads a collection.',
      viewCollection: 'View this collection'
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
      suggestionFailed: 'Impossible d’envoyer la suggestion pour le moment.',
      bookIslandTour: 'Réserver une excursion',
      islandTourTitle: 'Réservez votre excursion',
      islandTourDescription: 'Laissez vos coordonnées et nous reviendrons vers vous.',
      nameLabel: 'Nom',
      contactLabel: 'Contact',
      dateLabel: 'Date de l’excursion',
      enterName: 'Entrez votre nom',
      enterContact: 'Entrez votre contact',
      cancel: 'Annuler',
      submitBooking: 'Envoyer la réservation',
      bookingNeedName: 'Veuillez entrer votre nom.',
      bookingNeedContact: 'Veuillez entrer vos coordonnées.',
      bookingNeedDate: 'Veuillez choisir une date.',
      bookingSaved: 'Demande enregistrée. Nous vous contacterons bientôt.',
      mapLabel: 'Carte',
      detailsLabel: 'Détails',
      learnMore: 'En savoir plus',
      photoMemoriesTitle: 'Souvenirs photo',
      photoMemoriesDesc: 'Moments téléversés sur cette carte postale.',
      noPhotosTitle: 'Aucune photo',
      noPhotosDesc: 'Connectez-vous en tant que collectionneur pour ajouter des souvenirs.',
      noRelatedTitle: 'Aucune carte postale liée',
      noRelatedDesc: 'Les cartes postales liées apparaîtront ici.',
      viewCollection: 'Voir cette collection'
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
      suggestionFailed: 'Сейчас не удалось отправить предложение.',
      bookIslandTour: 'Забронировать тур',
      islandTourTitle: 'Забронируйте тур по острову',
      islandTourDescription: 'Оставьте имя и контакты, мы свяжемся с вами.',
      nameLabel: 'Имя',
      contactLabel: 'Контакт',
      dateLabel: 'Дата тура',
      enterName: 'Введите имя',
      enterContact: 'Введите контакт',
      cancel: 'Отмена',
      submitBooking: 'Отправить',
      bookingNeedName: 'Пожалуйста, введите имя.',
      bookingNeedContact: 'Пожалуйста, введите контакты.',
      bookingNeedDate: 'Пожалуйста, выберите дату.',
      bookingSaved: 'Заявка сохранена. Мы скоро свяжемся с вами.',
      mapLabel: 'Карта',
      detailsLabel: 'Детали',
      learnMore: 'Подробнее',
      photoMemoriesTitle: 'Фотографии-воспоминания',
      photoMemoriesDesc: 'Моменты, прикреплённые к этой открытке.',
      noPhotosTitle: 'Фотографий пока нет',
      noPhotosDesc: 'Войдите как коллекционер, чтобы добавить воспоминания.',
      noRelatedTitle: 'Связанных открыток нет',
      noRelatedDesc: 'Связанные открытки появятся здесь.',
      viewCollection: 'Открыть коллекцию'
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
      suggestionFailed: '지금은 건의를 보낼 수 없습니다.',
      bookIslandTour: '섬 투어 예약',
      islandTourTitle: '섬 투어를 예약하세요',
      islandTourDescription: '이름과 연락처를 남겨주시면 투어 가능 여부를 알려드립니다.',
      nameLabel: '이름',
      contactLabel: '연락처',
      dateLabel: '투어 날짜',
      enterName: '이름을 입력하세요',
      enterContact: '연락처를 입력하세요',
      cancel: '취소',
      submitBooking: '예약 신청',
      bookingNeedName: '이름을 입력해주세요.',
      bookingNeedContact: '연락처를 입력해주세요.',
      bookingNeedDate: '투어 날짜를 선택해주세요.',
      bookingSaved: '예약 요청이 저장되었습니다. 곧 연락드리겠습니다.',
      mapLabel: '지도',
      detailsLabel: '자세히',
      learnMore: '더 알아보기',
      photoMemoriesTitle: '사진 추억',
      photoMemoriesDesc: '이 엽서에 업로드된 순간들.',
      noPhotosTitle: '사진이 없습니다',
      noPhotosDesc: '수집자로 로그인하면 추억을 추가할 수 있어요.',
      noRelatedTitle: '관련 엽서 없음',
      noRelatedDesc: '관련 엽서가 여기에 표시됩니다.',
      viewCollection: '컬렉션 보기'
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
      suggestionFailed: '暂时无法发送建议。',
      bookIslandTour: '预订岛屿游',
      islandTourTitle: '预订您的岛屿游',
      islandTourDescription: '留下您的姓名和联系方式，我们会尽快联系您。',
      nameLabel: '姓名',
      contactLabel: '联系方式',
      dateLabel: '游览日期',
      enterName: '请输入姓名',
      enterContact: '请输入联系方式',
      cancel: '取消',
      submitBooking: '提交预订',
      bookingNeedName: '请输入姓名。',
      bookingNeedContact: '请输入联系方式。',
      bookingNeedDate: '请选择游览日期。',
      bookingSaved: '预订请求已保存，我们会尽快联系您。',
      mapLabel: '地图',
      detailsLabel: '详情',
      learnMore: '了解更多',
      photoMemoriesTitle: '照片回忆',
      photoMemoriesDesc: '上传到这张明信片的瞬间。',
      noPhotosTitle: '暂无照片',
      noPhotosDesc: '以收藏者身份登录即可添加回忆。',
      noRelatedTitle: '暂无相关明信片',
      noRelatedDesc: '相关明信片将显示在这里。',
      viewCollection: '查看此合集'
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
  let showMapModal = false;
  let tourBookingStatus = '';
  let imageFieldPlaceholder = MEMORY_PROMPTS_BY_LANGUAGE.en[0];
  let inputUsername = '';
  let inputUserId = '';
  let lightboxImageSrc = '';
  let currentLanguage = 'en';
  let lightboxImageAlt = 'Image preview';
  let lightboxImageUrl = '';
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
    if (typeof value === 'function') return value(params);
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
    if (lightboxImageSrc) lightboxImageAlt = t('imagePreview');
    if (shouldPersist) safeSetLocalStorageValue(LOCAL_STORAGE_LANGUAGE_KEY, currentLanguage);
  }

  function normalizeCredential(value) {
    return String(value ?? '').trim().toLowerCase();
  }

  function getCollectorName(collectorValue) {
    if (typeof collectorValue === 'string') return collectorValue;
    return collectorValue?.visitorName || collectorValue?.name || collectorValue?.username || '';
  }

  function getCollectorUsername(collectorValue) {
    if (typeof collectorValue === 'string') return collectorValue;
    return collectorValue?.username || collectorValue?.visitorName || collectorValue?.name || '';
  }

  function getCollectorUserId(collectorValue) {
    if (typeof collectorValue === 'string') return '';
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
    if (shouldPersist) safeSetLocalStorageValue(LOCAL_STORAGE_THEME_KEY, activeTheme);
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
    if (Array.isArray(data)) return data;
    if (data && typeof data === 'object') {
      if (Array.isArray(data.visitorCollections)) return [data, ...data.visitorCollections];
      const nestedArrayKeys = ['collections', 'data', 'results', 'items', 'records', 'rows'];
      for (const key of nestedArrayKeys) {
        if (Array.isArray(data[key])) return data[key];
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
    if (activePostcardTarget && activePostcardTarget !== 'garden-memories') return activePostcardTarget;
    if (scannedPostcardDetails?.collectionUniqueID) {
      activePostcardTarget = scannedPostcardDetails.collectionUniqueID;
      return activePostcardTarget;
    }
    if (scannedPostcardDetails?.id) {
      activePostcardTarget = scannedPostcardDetails.id;
      return activePostcardTarget;
    }
    if (typeof window === 'undefined') return DEFAULT_COLLECTION_STR;
    const urlParams = new URLSearchParams(window.location.search);
    const collectionStrParam = urlParams.get('collectionStr');
    if (collectionStrParam) {
      activePostcardTarget = collectionStrParam;
      return activePostcardTarget;
    }
    const pathSegments = window.location.pathname
      .split('/')
      .map((segment) => segment.trim())
      .filter(Boolean);
    const lastPathSegment = pathSegments[pathSegments.length - 1];
    if (lastPathSegment && lastPathSegment !== 'garden-memories') {
      activePostcardTarget = lastPathSegment;
    } else {
      activePostcardTarget = DEFAULT_COLLECTION_STR;
    }
    return activePostcardTarget;
  }

  function getPostcardDetailsApiUrl() {
    return `${POSTCARD_DETAILS_API_BASE_URL}${getCollectionStrFromUrl()}/`;
  }

  async function fetchLookPlaceData() {
    const headers = { 'Content-Type': 'application/json' };
    if (ACCEPT_HEADER.includes('application/json')) headers['Accept'] = 'application/json';

    const response = await fetch(getPostcardDetailsApiUrl(), {
      method: 'POST',
      headers,
      body: JSON.stringify({
        username: activeUsername,
        userID: activeUserId,
        collectionStr: getCollectionStrFromUrl()
      })
    });

    if (!response.ok) throw new Error(`Failed to fetch postcard details: ${response.status}`);
    const data = await response.json();
    if (data?.error) throw new Error(data.error);
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
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString(locale, {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  async function loadPostcardData() {
    isLoadingPostcard = true;
    credentialsError = '';

    await new Promise((resolve) => setTimeout(resolve, LOADING_DELAY_MS));

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
      history.replaceState({}, '', '/garden-memories/');
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
    tick().then(() => {
      const credentialsBox = document.getElementById('credentials-box');
      if (credentialsBox) credentialsBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }

  function getRotatingMemoryPrompt() {
    const memoryPrompts = getMemoryPrompts();
    if (!memoryPrompts.length) return t('memoryPromptFallback');
    const previousPromptIndex = Number.parseInt(safeGetLocalStorageValue(MEMORY_PROMPT_STORAGE_KEY) ?? '', 10);
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
    for (const file of files) formData.append('images', file);
    formData.append('imageField', uploadImageField.trim());
    formData.append('username', activeUsername);
    formData.append('userID', activeUserId);
    formData.append('collectionUniqueID', getCollectionStrFromUrl());

    const response = await fetch(UPLOAD_API_URL, { method: 'POST', body: formData });
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
    if (!Array.isArray(responseBody?.saved)) throw new Error(t('uploadResponseMissing'));
    return responseBody.saved;
  }

  function getUploadedImageUrl(savedItem, fallbackFile) {
    if (typeof savedItem === 'string') return savedItem;
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
        if (!imageUrl) return null;
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

    if (!newMemoryItems.length) return;

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
      { ...firstCollection, collectionMemory: [...newMemoryItems, ...existingMemory] },
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
    if (!files.length) return;
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

  function openMapModal() {
    showMapModal = true;
  }

  function closeMapModal() {
    showMapModal = false;
  }

  async function submitTourBooking() {
    const normalizedName = tourBookingName.trim();
    const normalizedContact = tourBookingContact.trim();
    const normalizedDate = tourBookingDate.trim();
    if (!normalizedName) return void (tourBookingError = t('bookingNeedName'));
    if (!normalizedContact) return void (tourBookingError = t('bookingNeedContact'));
    if (!normalizedDate) return void (tourBookingError = t('bookingNeedDate'));
    if (!window.emailjs || !isEmailJsReady) return void (tourBookingError = t('suggestionFailed'));

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
    if (event.key === 'Escape' && showTourBookingModal) closeTourBookingModal();
    if (event.key === 'Escape' && showMapModal) closeMapModal();
    if (event.key === 'Escape' && lightboxImageSrc) closeImagePreview();
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
    try {
      const response = await fetch(VISITOR_API_URL, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ username: normalizedUsername, userID: normalizedUserId })
      });
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Visitor registration failed:', response.status, errorText);
      } else {
        safeSetLocalStorageValue(LOCAL_STORAGE_USERNAME_KEY, normalizedUsername);
        safeSetLocalStorageValue(LOCAL_STORAGE_USER_ID_KEY, normalizedUserId);
        persistSession(normalizedUsername, normalizedUserId, null);
      }
    } catch (error) {
      console.error('Visitor registration request failed:', error);
    }
    showCredentialsForm = false;
    await loadPostcardData();
  }

  function openImagePreview(src, alt = t('imagePreview'), urlpassed = null) {
    if (!src) return;
    lightboxImageSrc = src;
    lightboxImageAlt = alt;
    lightboxImageUrl = urlpassed;
  }

  function closeImagePreview() {
    lightboxImageSrc = '';
    lightboxImageAlt = t('imagePreview');
    lightboxImageUrl = null;
  }

  function getSuggestionLastSentKey(username) {
    const normalizedUsername = normalizeCredential(username);
    return `${SUGGESTION_LAST_SENT_KEY_PREFIX}:${normalizedUsername || 'guest'}`;
  }

  function getSuggestionCooldownMessage(msRemaining) {
    const totalMinutes = Math.ceil(msRemaining / 60000);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    if (hours > 0) return `You can send another suggestion in ${hours}h ${minutes}m.`;
    return `You can send another suggestion in ${minutes}m.`;
  }

  async function sendSuggestion() {
    const guestMessage = suggestionMessage.trim();
    let senderContact = suggestionSenderContact.trim();
    if (!guestMessage) return void alert(t('suggestionNeedText'));
    if (!window.emailjs || !isEmailJsReady) return void alert(t('suggestionFailed'));

    const existingUsername = activeUsername?.trim();
    if (!existingUsername) {
      const promptedUsername = window.prompt('Please your name');
      if (!promptedUsername?.trim()) return;
      activeUsername = promptedUsername.trim();
      safeSetLocalStorageValue(LOCAL_STORAGE_USERNAME_KEY, activeUsername);
      alert('Username saved. Click Send again.');
      return;
    }
    if (!senderContact) {
      const promptedContact = window.prompt('Your contact');
      if (!promptedContact?.trim()) return;
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
        window.emailjs.init({ publicKey: EMAILJS_PUBLIC_KEY });
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
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link
    href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,500;9..144,700&family=Nunito:wght@400;600;700;800;900&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<svelte:window on:keydown={handleWindowKeydown} />

<div class="page">
  <header class="topbar">
    <div class="account-chip" aria-live="polite">
      <span class="account-name">
        {t('welcome', { name: $session.isGuest ? t('guest') : activeUsername || t('guest') })}
      </span>

      <div class="chip-controls">
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
          <button class="cta compact" type="button" on:click={openCreateAccountForm}>
            {t('enterAccount')}
          </button>
        {/if}
      </div>
    </div>
  </header>

  <section class="hero">
    {#if showCredentialsForm}
      <div id="credentials-box" class="credentials-box" aria-live="polite">
        <h3>{t('enterAccount')}</h3>
        <form class="credentials-form" on:submit|preventDefault={submitCredentials}>
          <label>
            {t('username')}
            <input bind:value={inputUsername} type="text" placeholder={t('enterUsername')} autocomplete="username" />
          </label>
          <label>
            {t('userId')}
            <input bind:value={inputUserId} type="text" placeholder={t('enterUserId')} autocomplete="off" />
          </label>
          {#if credentialsError}
            <p class="credentials-error">{credentialsError}</p>
          {/if}
          <button class="cta" type="submit">{t('saveAndContinue')}</button>
        </form>
      </div>
    {:else}
      <div class="hero-card">
        {#if isLoadingPostcard}
          <div class="loading-state">
            <span class="spinner" aria-hidden="true"></span>
            <span>{t('loadingImage')}</span>
          </div>
        {:else}
          <div class="hero-layout">
            <figure class="hero-image-col">
              <img
                id="scanned-postcard"
                src={scannedPostcardSrc}
                alt={t('scannedPostcardAlt')}
                loading="eager"
                decoding="async"
              />
            </figure>

            <div class="hero-info-col" id="scanned-postcard-meta">
              <h3 class="postcard-title">{scannedPostcardDetails.title}</h3>

              <dl class="meta-list">
                <div class="meta-row">
                  <dt>{t('location')}</dt>
                  <dd>{scannedPostcardDetails.location || '—'}</dd>
                </div>
                <div class="meta-row">
                  <dt>{t('collected')}</dt>
                  <dd>{formatCollectedDate(scannedPostcardDetails.collected) || '—'}</dd>
                </div>
                <div class="meta-row">
                  <dt>{t('collector')}</dt>
                  <dd>{scannedPostcardDetails.collector || '—'}</dd>
                </div>
              </dl>

              <div class="meta-actions">
                <button class="ghost" type="button" on:click={openMapModal} aria-label={t('mapLabel')}>
                  <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                    <path
                      d="M15.817.113A.5.5 0 0 1 16 .5v14a.5.5 0 0 1-.402.49l-5 1a.502.502 0 0 1-.196 0L5.5 15.01l-4.902.98A.5.5 0 0 1 0 15.5v-14a.5.5 0 0 1 .402-.49l5-1a.5.5 0 0 1 .196 0L10.5.99l4.902-.98a.5.5 0 0 1 .415.103zM10 1.91l-4-.8v12.98l4 .8V1.91zm1 12.98 4-.8V1.11l-4 .8v12.98zm-6-.8V1.11l-4 .8v12.98l4-.8z"
                      fill-rule="evenodd"
                    />
                  </svg>
                  <span>{t('mapLabel')}</span>
                </button>

                {#if scannedPostcardDetails.collectionPlaceDirect}
                  <a
                    class="cta compact"
                    href={`/places/${scannedPostcardDetails.collectionPlaceDirect}/${currentYear}/${currentMonth}/`}
                  >
                    {t('learnMore')}
                  </a>
                {/if}
              </div>

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
                    on:change={handleUploadSelection}
                  />
                  <textarea
                    id="modalImageField"
                    bind:value={uploadImageField}
                    class="image-field-input"
                    name="imageField"
                    rows="3"
                    on:input={handleImageFieldInput}
                    placeholder={imageFieldPlaceholder}
                  ></textarea>
                  {#if showUploadPictureButton}
                    <button class="cta" type="button" on:click={openUploadPicker} disabled={isUploadingImages}>
                      {isUploadingImages ? t('uploading') : t('uploadPicture')}
                    </button>
                  {/if}
                </div>
                {#if uploadStatus}
                  <p class="upload-status">{uploadStatus}</p>
                {/if}
              {/if}
            </div>
          </div>
        {/if}
      </div>
    {/if}
  </section>

  <div class="gardenhead">
    <div class="postcard-head-title">
      <img src={GardenHeadLogo} alt="Memory Garden Home Logo" class="logo" />
    </div>

    {#if $session.isGuest}
      <div class="logo-frame">
        <img src={GardenBodyLogo} alt="Memory Garden Home Logo" class="logo" />
      </div>
      <div class="logo-frame">
        <img src={GardenBorderLogo} alt="Memory Garden Home Logo" class="logo" />
      </div>
      <div class="hero-copy">
        <p class="eyebrow">{t('eyebrow')}</p>
        <h1>{t('brandTitle')}</h1>
        <p class="subtext">{t('subtext')}</p>
      </div>
    {/if}
  </div>

  <section class="support-grid" aria-label="Postcard supporting memories">
    <div class="support-card">
      <div class="support-card-header">
        <div class="support-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path
              d="M4 7.5A2.5 2.5 0 0 1 6.5 5h11A2.5 2.5 0 0 1 20 7.5v9a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 16.5v-9Zm2.5-.8a.8.8 0 0 0-.8.8v7.2l3.7-3.2a1.4 1.4 0 0 1 1.8 0l2.2 1.8 1.2-1.1a1.4 1.4 0 0 1 1.9 0l1.8 1.7V7.5a.8.8 0 0 0-.8-.8h-11Zm11.8 9.5-2.7-2.6-1.2 1.1a1.4 1.4 0 0 1-1.8.1l-2.3-1.9-4.1 3.6c.1.5.5.8 1 .8h10.3c.4 0 .7-.2.8-.5v-.6ZM8.3 9.2a1.1 1.1 0 1 1 2.2 0 1.1 1.1 0 0 1-2.2 0Z"
            />
          </svg>
        </div>
        <div>
          <h2>{t('photoMemoriesTitle')}</h2>
          <p>{t('photoMemoriesDesc')}</p>
        </div>
      </div>

      {#if getCollectionMemoryItems().length}
        <div class="memory-grid">
          {#each getCollectionMemoryItems() as memory}
            {#if memory.image}
              <button class="image-trigger" type="button" on:click={() => openImagePreview(memory.image, memory.about)}>
                <img class="memory-image" src={memory.image} alt={memory.about} loading="lazy" decoding="async" />
              </button>
            {/if}
          {/each}
        </div>
      {:else}
        <div class="empty-support-card">
          <strong>{t('noPhotosTitle')}</strong>
          <p>{t('noPhotosDesc')}</p>
        </div>
      {/if}
    </div>

    <div class="support-card">
      <div class="support-card-header">
        <div class="support-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path
              d="M6 4.5h12a2 2 0 0 1 2 2v9.8a2 2 0 0 1-2 2H8.2L4 21V6.5a2 2 0 0 1 2-2Zm0 2v10.8l1.6-1h10.4V6.5H6Zm2.3 2.2h7.4v1.6H8.3V8.7Zm0 3.2h5.2v1.6H8.3v-1.6Z"
            />
          </svg>
        </div>
        <div>
          <h2>{t('gridTitle')}</h2>
        </div>
      </div>

      {#if postcardMemories.length}
        <div class="related-memory-grid">
          {#each postcardMemories as postcard}
            <div class="memory-card">
              <button
                class="image-trigger"
                type="button"
                on:click={() => openImagePreview(postcard.src, postcard.title, `/garden/look/${postcard.id}/`)}
                aria-label={`View ${postcard.title}`}
              >
                <div class="memory-image-collection" style="background-image: url({postcard.src})"></div>
              </button>
            </div>
          {/each}
        </div>
      {:else}
        <div class="empty-support-card">
          <strong>{t('noRelatedTitle')}</strong>
          <p>{t('noRelatedDesc')}</p>
        </div>
      {/if}
    </div>
  </section>

  {#if showTourBookingModal}
    <div class="modal-backdrop" role="presentation">
      <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="tour-booking-title" tabindex="-1">
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

  {#if showMapModal}
    <div class="modal-backdrop" role="presentation" on:click={closeMapModal}>
      <div
        class="map-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="map-modal-title"
        tabindex="-1"
        on:click|stopPropagation
      >
        <button class="map-modal-close" type="button" on:click={closeMapModal} aria-label="Close map">×</button>
        <div class="map-container">
          <iframe
            id="map-modal-iframe"
            title="Map of {scannedPostcardDetails.location}"
            width="100%"
            height="100%"
            style="border:0"
            src="/garden/map/{scannedPostcardDetails.collectionPlaceDirect}/"
            allowfullscreen
            loading="lazy"
          ></iframe>
        </div>
      </div>
    </div>
  {/if}

  {#if lightboxImageSrc}
    <div class="image-lightbox" role="dialog" aria-modal="true" aria-label={lightboxImageAlt}>
      <button class="lightbox-backdrop-button" type="button" on:click={closeImagePreview} aria-label="Close preview"></button>
      <div class="lightbox-content">
        <img class="lightbox-image" src={lightboxImageSrc} alt={lightboxImageAlt} decoding="async" />
        {#if lightboxImageAlt}
          <p class="lightbox-caption">{lightboxImageAlt}</p>
        {/if}
        {#if lightboxImageUrl}
          <a class="view-collection-link" href={lightboxImageUrl} rel="noopener noreferrer">
            {t('viewCollection')}
          </a>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  /* ============================================================
     Design tokens — Garden Home palette
     ============================================================ */

  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    /* ---- Light theme (default) ---- */
    --bg-page: #faf6ee;
    --bg-grad-a: #fdfbf5;
    --bg-grad-b: #f6f1e4;
    --bg-grad-c: #eef3e8;

    --surface: #ffffff;
    --surface-soft: #f7f3e8;
    --surface-tint: #edf3e8;

    --primary: #3e7a56;
    --primary-hover: #325f44;
    --primary-soft: #e6f0ea;
    --primary-contrast: #ffffff;

    --accent: #c97b4a;
    --accent-hover: #b3683a;
    --accent-soft: #f8e9dd;
    --accent-contrast: #ffffff;

    --text-strong: #1b2a22;
    --text: #3a4741;
    --text-soft: #6d7b73;
    --text-muted: #96a199;

    --border: #e5dfce;
    --border-strong: #c9c2a9;
    --border-dashed: rgba(62, 122, 86, 0.4);

    --danger: #c0392b;
    --danger-soft: #fce9e6;

    --shadow-sm: 0 1px 2px rgba(27, 42, 34, 0.05);
    --shadow-md: 0 8px 24px rgba(27, 42, 34, 0.07);
    --shadow-lg: 0 20px 48px rgba(27, 42, 34, 0.1);

    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 18px;
    --radius-pill: 999px;

    margin: 0;
    font-family: 'Nunito', 'Arial Rounded MT Bold', 'Segoe UI', system-ui, sans-serif;
    background: var(--bg-page);
    color: var(--text);
    -webkit-font-smoothing: antialiased;
    transition: background-color 0.25s ease, color 0.25s ease;
  }

  :global(body[data-theme='dark']) {
    --bg-page: #0d1411;
    --bg-grad-a: #101913;
    --bg-grad-b: #0d1411;
    --bg-grad-c: #0a100d;

    --surface: #16201b;
    --surface-soft: #1c2822;
    --surface-tint: #1f2e24;

    --primary: #7dbe93;
    --primary-hover: #96cda8;
    --primary-soft: rgba(125, 190, 147, 0.14);
    --primary-contrast: #0d1411;

    --accent: #e0a876;
    --accent-hover: #edb98c;
    --accent-soft: rgba(224, 168, 118, 0.14);
    --accent-contrast: #0d1411;

    --text-strong: #eff5ef;
    --text: #c9d3cb;
    --text-soft: #8b9a8f;
    --text-muted: #66746a;

    --border: #24322a;
    --border-strong: #35463b;
    --border-dashed: rgba(125, 190, 147, 0.35);

    --danger: #f58c7e;
    --danger-soft: rgba(245, 140, 126, 0.12);

    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.4);
    --shadow-lg: 0 20px 48px rgba(0, 0, 0, 0.5);
  }

  /* ============================================================
     Page
     ============================================================ */

  .page {
    margin: 0 auto;
    background: linear-gradient(
      180deg,
      var(--bg-grad-a) 0%,
      var(--bg-grad-b) 54%,
      var(--bg-grad-c) 100%
    );
    min-height: 100vh;
    transition: background 0.25s ease;
  }

  /* ============================================================
     Top bar
     ============================================================ */

  .topbar {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding: 0.7rem 1rem;
    gap: 1rem;
  }

  .account-chip {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .account-name {
    color: var(--text-strong);
    font-weight: 700;
    font-size: 0.85rem;
  }

  .chip-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .lang-switch {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
  }

  .lang-btn {
    font: inherit;
    border-radius: var(--radius-pill);
    background: var(--surface);
    color: var(--text);
    min-height: 1.9rem;
    padding: 0.2rem 0.55rem;
    cursor: pointer;
    font-size: 0.72rem;
    line-height: 1;
    font-weight: 600;
    border: 1px solid var(--border);
    transition: background 0.15s, color 0.15s, border-color 0.15s;
  }

  .lang-btn:hover {
    border-color: var(--primary);
    color: var(--primary);
  }

  .lang-btn.is-active {
    background: var(--primary);
    border-color: var(--primary);
    color: var(--primary-contrast);
  }

  .theme-toggle {
    font: inherit;
    border-radius: var(--radius-pill);
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-strong);
    width: 2rem;
    height: 2rem;
    padding: 0;
    cursor: pointer;
    font-size: 0.9rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    transition: background 0.15s, border-color 0.15s;
  }

  .theme-toggle:hover {
    border-color: var(--primary);
  }

  /* ============================================================
     Buttons
     ============================================================ */

  .cta,
  .ghost {
    font: inherit;
    border: none;
    border-radius: var(--radius-pill);
    padding: 0.6rem 1.05rem;
    cursor: pointer;
    font-weight: 700;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    transition: background 0.15s, border-color 0.15s, color 0.15s, transform 0.15s;
  }

  .cta {
    background: var(--primary);
    color: var(--primary-contrast);
  }
  .cta:hover:not(:disabled) {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }
  .cta:active:not(:disabled) {
    transform: translateY(0);
  }
  .cta:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .cta.compact {
    padding: 0.45rem 0.85rem;
    font-size: 0.82rem;
  }

  .ghost {
    background: transparent;
    color: var(--primary);
    border: 1px solid var(--primary);
  }
  .ghost:hover {
    background: var(--primary-soft);
  }

  /* ============================================================
     Hero
     ============================================================ */

  .hero {
    width: min(100% - 2rem, 1080px);
    margin: 0 auto;
    padding: 0 0 1rem;
  }

  .hero-card {
    overflow: hidden;
    box-shadow: var(--shadow-md);
    transition: background 0.25s ease, border-color 0.25s ease;
  }

  .hero-layout {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.25rem;
    padding: 1rem;
  }

  @media (min-width: 760px) {
    .hero-layout {
      grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
      align-items: stretch;
      gap: 1.5rem;
      padding: 1.25rem;
    }
  }

  .hero-image-col {
    margin: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  #scanned-postcard {
    display: block;
    width: 100%;
    height: auto;
    max-height: 70vh;
    object-fit: cover;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
  }

  .hero-info-col {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-width: 0;
  }

  .postcard-title {
    margin: 0;
    color: var(--text-strong);
    font-family: 'Fraunces', Georgia, serif;
    font-size: clamp(1.3rem, 2.4vw, 1.75rem);
    font-weight: 500;
    line-height: 1.2;
  }

  .meta-list {
    margin: 0;
    display: grid;
    gap: 0.55rem;
  }

  .meta-row {
    display: grid;
    grid-template-columns: minmax(6.5rem, auto) 1fr;
    gap: 0.75rem;
    align-items: baseline;
    padding-bottom: 0.55rem;
    border-bottom: 1px solid var(--border);
  }
  .meta-row:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }

  .meta-row dt {
    margin: 0;
    color: var(--text-soft);
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .meta-row dd {
    margin: 0;
    color: var(--text);
    font-size: 0.95rem;
    line-height: 1.4;
    overflow-wrap: anywhere;
  }

  .meta-actions {
    display: flex;
    gap: 0.55rem;
    flex-wrap: wrap;
    margin-top: auto;
  }

  /* "Learn more" uses the warm accent */
  .meta-actions .cta.compact {
    background: var(--accent);
    color: var(--accent-contrast);
  }
  .meta-actions .cta.compact:hover {
    background: var(--accent-hover);
  }

  .loading-state {
    min-height: 240px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    color: var(--text-soft);
    padding: 1.25rem;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border-radius: var(--radius-pill);
    border: 2px solid var(--border);
    border-top-color: var(--primary);
    animation: spin 0.8s linear infinite;
  }

  /* ============================================================
     Collector upload (hero)
     ============================================================ */

  .hero-actions {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    align-items: flex-start;
    padding-top: 0.75rem;
    border-top: 1px dashed var(--border-dashed);
  }

  .upload-input {
    display: none;
  }

  .image-field-input {
    font: inherit;
    color: var(--text);
    background: var(--surface-soft);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.65rem 0.75rem;
    width: 100%;
    min-height: 5rem;
    line-height: 1.4;
    resize: vertical;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .image-field-input:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px var(--primary-soft);
  }
  .image-field-input::placeholder {
    color: var(--text-muted);
  }

  .upload-status {
    margin: 0;
    color: var(--text-soft);
    font-size: 0.9rem;
  }

  /* ============================================================
     Credentials box
     ============================================================ */

  .credentials-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.25rem;
    box-shadow: var(--shadow-md);
    max-width: 480px;
    margin: 0 auto;
  }

  .credentials-box h3 {
    margin: 0;
    font-size: 1.1rem;
    color: var(--text-strong);
  }

  .credentials-form {
    margin-top: 0.9rem;
    display: grid;
    gap: 0.75rem;
  }

  .credentials-form label {
    display: grid;
    gap: 0.35rem;
    font-size: 0.86rem;
    font-weight: 700;
    color: var(--text-soft);
  }

  .credentials-form input {
    font: inherit;
    color: var(--text);
    background: var(--surface-soft);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.6rem 0.7rem;
    font-size: 1rem;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .credentials-form input:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px var(--primary-soft);
  }
  .credentials-form input::placeholder {
    color: var(--text-muted);
  }

  .credentials-error {
    margin: 0;
    color: var(--danger);
    font-size: 0.9rem;
  }

  /* ============================================================
     Garden head (logos + brand copy)
     ============================================================ */

  .gardenhead {
    text-align: center;
    padding: 1.2rem 1rem 0.45rem;
  }

  .postcard-head-title {
    width: min(100%, 640px);
    margin: 0 auto;
    display: grid;
    justify-items: center;
    gap: 0.35rem;
  }

  .postcard-head-title .logo,
  .logo-frame .logo {
    display: block;
    max-width: 100%;
    height: auto;
  }

  .logo-frame {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 0.15rem 1rem;
    margin: 0 auto;
    max-width: 640px;
  }

  .hero-copy {
    display: grid;
    justify-items: center;
    gap: 0.45rem;
    margin: 0.6rem auto 1rem;
    text-align: center;
    padding: 0 1rem;
  }

  .hero-copy h1 {
    margin: 0;
    max-width: 12ch;
    color: var(--text-strong);
    font-family: 'Fraunces', Georgia, serif;
    font-size: clamp(2.2rem, 6vw, 4.2rem);
    font-style: italic;
    font-weight: 300;
    line-height: 0.95;
  }

  .eyebrow {
    margin: 0;
    color: var(--primary);
    letter-spacing: 0.08em;
    font-size: 0.75rem;
    font-weight: 700;
  }

  .subtext {
    margin: 0;
    max-width: 42rem;
    color: var(--text-soft);
    font-size: 1rem;
    line-height: 1.55;
    font-weight: 500;
  }

  /* ============================================================
     Support grid
     ============================================================ */

  .support-grid {
    width: min(100% - 2rem, 1080px);
    margin: 0 auto;
    padding: 0.75rem 0 2.5rem;
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
    align-items: start;
  }

  @media (min-width: 760px) {
    .support-grid {
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    }
  }

  .support-card {
    min-width: 0;
    padding: 1rem;
    box-shadow: var(--shadow-md);
    transition: background 0.25s ease, border-color 0.25s ease;
  }

  .support-card-header {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
    margin-bottom: 0.85rem;
  }

  .support-icon {
    width: 2.3rem;
    height: 2.3rem;
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-pill);
    background: var(--primary-soft);
    border: 1px solid var(--border-dashed);
    color: var(--primary);
  }

  .support-icon svg {
    width: 1.25rem;
    height: 1.25rem;
    fill: currentColor;
  }

  .support-card h2 {
    margin: 0;
    color: var(--text-strong);
    font-size: 1.15rem;
    font-weight: 800;
    line-height: 1.2;
  }

  .support-card-header p {
    margin: 0.22rem 0 0;
    color: var(--text-soft);
    font-size: 0.88rem;
    line-height: 1.42;
  }

  .memory-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  }

  .image-trigger {
    border: none;
    background: transparent;
    padding: 0;
    margin: 0;
    width: 100%;
    cursor: zoom-in;
    display: block;

    overflow: hidden;
  }

  .memory-image {
    display: block;
    width: 100%;
    height: 126px;
    object-fit: cover;
    transition: transform 0.25s ease;
  }
  .image-trigger:hover .memory-image {
    transform: scale(1.03);
  }

  .related-memory-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(128px, 1fr));
    gap: 0.6rem;
  }

  .memory-image-collection {
    width: 100%;
    aspect-ratio: 1.2 / 1;
    border-radius: var(--radius-sm);
    background-size: cover;
    background-position: center;
    box-shadow: inset 0 0 0 1px rgba(27, 42, 34, 0.08);
    transition: transform 0.25s ease;
  }
  .image-trigger:hover .memory-image-collection {
    transform: scale(1.03);
  }

  .empty-support-card {
    min-height: 126px;
    display: grid;
    align-content: center;
    gap: 0.35rem;
    padding: 1rem;
    border: 1px dashed var(--border-dashed);
    border-radius: var(--radius-md);
    background: var(--surface-soft);
    color: var(--text-soft);
  }

  .empty-support-card strong {
    color: var(--text-strong);
    font-size: 0.98rem;
  }
  .empty-support-card p {
    margin: 0;
    color: var(--text-soft);
    font-size: 0.9rem;
    line-height: 1.45;
  }

  /* ============================================================
     Modals
     ============================================================ */

  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(13, 20, 17, 0.65);
    backdrop-filter: blur(10px);
  }

  .modal-card {
    width: min(100%, 420px);
    border-radius: var(--radius-lg);
    border: 1px solid var(--border);
    background: var(--surface);
    padding: 1rem;
    box-shadow: var(--shadow-lg);
  }

  .modal-card h3 {
    margin: 0;
    font-size: 1.1rem;
    color: var(--text-strong);
  }
  .modal-copy {
    margin: 0.55rem 0 0;
    color: var(--text-soft);
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
    color: var(--text-soft);
    font-size: 0.9rem;
    font-weight: 600;
  }
  .tour-booking-form input {
    font: inherit;
    color: var(--text);
    background: var(--surface-soft);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.75rem 0.8rem;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  .tour-booking-form input:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px var(--primary-soft);
  }
  .tour-booking-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.65rem;
    flex-wrap: wrap;
  }

  .map-modal {
    position: relative;
    display: flex;
    flex-direction: column;
    width: 90%;
    max-width: 800px;
    height: 80vh;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-lg);
  }
  .map-modal h3 {
    margin: 0 0 1rem 0;
    color: var(--text-strong);
    font-size: 1.2rem;
    font-weight: 600;
  }
  .map-modal-close {
    position: absolute;
    top: 1rem;
    right: 1rem;
    width: 40px;
    height: 40px;
    padding: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: 26px;
    line-height: 1;
    cursor: pointer;
    color: var(--text-strong);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1;
    transition: background 0.15s, border-color 0.15s;
  }
  .map-modal-close:hover {
    background: var(--surface-soft);
    border-color: var(--border-strong);
  }
  .map-container {
    flex: 1;
    width: 100%;
    overflow: hidden;
    border-radius: var(--radius-sm);
  }
  .map-container iframe {
    display: block;
    width: 100%;
    height: 100%;
  }

  /* ============================================================
     Lightbox
     ============================================================ */

  .image-lightbox {
    position: fixed;
    inset: 0;
    z-index: 999;
    background: rgba(7, 10, 15, 0.94);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }

  .lightbox-backdrop-button {
    position: absolute;
    inset: 0;
    background: transparent;
    border: none;
    cursor: zoom-out;
    padding: 0;
  }

  .lightbox-content {
    position: relative;
    z-index: 1;
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
    border-radius: var(--radius-md);
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45);
  }

  .lightbox-caption {
    margin: 0;
    color: #f4f6fb;
    font-size: 0.95rem;
    text-align: center;
    max-width: 90vw;
    line-height: 1.4;
  }

  .view-collection-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: max-content;
    padding: 0.55rem 0.9rem;
    border-radius: var(--radius-pill);
    border: 1px solid var(--accent);
    background: transparent;
    color: var(--accent);
    font-size: 0.95rem;
    font-weight: 700;
    text-decoration: none;
    transition: background 180ms, color 180ms, transform 180ms;
  }
  .view-collection-link:hover {
    background: var(--accent);
    color: var(--accent-contrast);
    transform: translateY(-1px);
  }

  /* ============================================================
     Animations
     ============================================================ */

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .spinner,
    .image-trigger:hover .memory-image,
    .image-trigger:hover .memory-image-collection {
      animation: none;
      transition: none;
      transform: none;
    }
  }

  /* ============================================================
     Mobile
     ============================================================ */

  @media (max-width: 680px) {
    .hero {
      width: min(100% - 1.25rem, 1080px);
    }
    .support-grid {
      width: min(100% - 1.25rem, 1080px);
    }
    .hero-layout {
      padding: 0.9rem;
    }
    .topbar {
      padding: 0.6rem 0.75rem;
    }
    .account-chip {
      width: 100%;
      justify-content: space-between;
    }
    .chip-controls {
      gap: 0.4rem;
    }
    .meta-actions .cta,
    .meta-actions .ghost,
    .hero-actions .cta,
    .hero-actions .image-field-input {
      width: 100%;
      min-height: 44px;
    }
    .memory-grid {
      grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
    }
    .memory-image {
      height: 90px;
    }
    .credentials-form input {
      font-size: 16px;
    }
  }
</style>