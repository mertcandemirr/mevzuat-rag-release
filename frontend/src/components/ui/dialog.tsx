import * as DialogPrimitive from '@radix-ui/react-dialog';
import {X} from 'lucide-react';
import {cn} from '../../lib/utils';
import type {ComponentProps} from 'react';
export const Dialog=DialogPrimitive.Root;
export const DialogTitle=DialogPrimitive.Title;
export const DialogDescription=DialogPrimitive.Description;
export function DialogContent({className,children,...props}:ComponentProps<typeof DialogPrimitive.Content>){return <DialogPrimitive.Portal><DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"/><DialogPrimitive.Content className={cn('dialog-content fixed z-50 border border-[var(--border)] bg-[var(--surface)] p-7 text-[var(--text)] shadow-2xl',className)} {...props}>{children}<DialogPrimitive.Close className="absolute right-5 top-5 rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--hover)]" aria-label="Paneli kapat"><X size={18}/></DialogPrimitive.Close></DialogPrimitive.Content></DialogPrimitive.Portal>}
