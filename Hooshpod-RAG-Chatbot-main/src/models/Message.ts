import { Document, Schema, model } from "mongoose";

export interface MessageDocument extends Document {
  userId: string;
  sessionId: string;
  message: string;
  response: string;
  cached: boolean;
  meta?: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

const messageSchema = new Schema<MessageDocument>(
  {
    userId: { type: String, required: true, index: true },
    sessionId: { type: String, required: true, index: true },
    message: { type: String, required: true },
    response: { type: String, required: true },
    cached: { type: Boolean, default: false },
    meta: { type: Schema.Types.Mixed, default: {} },
  },
  {
    timestamps: true,
    versionKey: false,
  }
);

messageSchema.index({ userId: 1, createdAt: 1 });
messageSchema.index({ sessionId: 1, createdAt: 1 });

export const Message = model<MessageDocument>("Message", messageSchema);
