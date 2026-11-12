import * as React from 'react';
import {Slot} from '@radix-ui/react-slot';
import {cva,type VariantProps} from 'class-variance-authority';
import {cn} from '../../lib/utils';
const variants=cva('inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 disabled:pointer-events-none disabled:opacity-40',{variants:{variant:{default:'bg-[var(--accent)] text-[#19212b] hover:brightness-110',ghost:'text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--text)]',outline:'border border-[var(--border)] text-[var(--text)] hover:bg-[var(--hover)]'},size:{default:'h-10 px-4',icon:'h-9 w-9'}},defaultVariants:{variant:'default',size:'default'}});
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>,VariantProps<typeof variants>{asChild?:boolean}
export const Button=React.forwardRef<HTMLButtonElement,ButtonProps>(({className,variant,size,asChild=false,...props},ref)=>{const Comp=asChild?Slot:'button';return <Comp ref={ref} className={cn(variants({variant,size,className}))} {...props}/>});Button.displayName='Button';
