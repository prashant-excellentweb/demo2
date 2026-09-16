import { FileText, Paperclip } from "lucide-react";

import { attachmentUrl } from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import type { Attachment } from "@/types";

/**
 * Attachments already sent with a message.
 *
 * Images are loaded from the attachment endpoint rather than inlined as base64,
 * so revisiting a long conversation does not re-download the bytes.
 */
export function AttachmentChips({ attachments }: { attachments: Attachment[] }) {
  if (attachments.length === 0) return null;

  const images = attachments.filter((item) => item.is_image);
  const files = attachments.filter((item) => !item.is_image);

  return (
    <div className="space-y-2">
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((image) => (
            <a
              key={image.id}
              href={attachmentUrl(image.id)}
              target="_blank"
              rel="noreferrer noopener"
              className="block overflow-hidden rounded-xl border border-line"
            >
              <img
                src={attachmentUrl(image.id)}
                alt={image.filename}
                loading="lazy"
                className="max-h-56 w-auto max-w-[18rem] object-cover"
              />
            </a>
          ))}
        </div>
      )}

      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((file) => (
            <a
              key={file.id}
              href={attachmentUrl(file.id)}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-xs transition-colors hover:border-accent/40"
            >
              {file.content_type === "application/pdf" ? (
                <FileText className="size-4 shrink-0 text-accent" />
              ) : (
                <Paperclip className="size-4 shrink-0 text-accent" />
              )}
              <span className="max-w-[12rem] truncate font-medium text-fg">
                {file.filename}
              </span>
              <span className="text-fg-subtle">{formatBytes(file.size_bytes)}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
