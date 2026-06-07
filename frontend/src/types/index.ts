export type AuthResponse = {
  accessToken: string;
  refreshToken: string;
  userId: string;
  username: string;
  email: string;
  fullName: string;
  role: string;
};

export type DocumentItem = {
  id: string;
  fileName: string;
  fileType: string;
  sizeBytes: number;
  status: "UPLOADED" | "PROCESSING" | "READY" | "FAILED";
  documentType?: string;
  processingMessage?: string;
  createdAt: string;
  updatedAt: string;
};

export type Chunk = {
  id: string;
  chunkIndex: number;
  sectionType: string;
  heading?: string;
  parentHeading?: string;
  text: string;
  pageNumber?: number;
  riskLevel: string;
  importance: string;
  citationLabel?: string;
};

export type Entity = {
  id: string;
  entityType: string;
  entityValue: string;
  confidence: number;
  pageNumber?: number;
  sourceChunkIndex?: number;
};

export type InsightResponse = {
  document: DocumentItem;
  entities: Entity[];
  coverage: Chunk[];
  exclusions: Chunk[];
  waitingPeriods: Chunk[];
  riskAlerts: Chunk[];
  allChunks: Chunk[];
};

export type Citation = {
  citationLabel?: string;
  pageNumber?: number;
  sectionType: string;
  heading?: string;
  text: string;
  score: number;
};

export type ChatResponse = {
  sessionId: string;
  answer: string;
  confidence: number;
  intent: string;
  verified: boolean;
  citations: Citation[];
  riskAlerts: string[];
};

export type ChatMessage = {
  id: string;
  role: "USER" | "ASSISTANT";
  content: string;
  confidence?: number;
  citationsJson?: string;
  riskAlertsJson?: string;
  createdAt: string;
};
