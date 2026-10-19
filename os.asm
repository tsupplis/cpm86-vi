; Local subset of cpm86-hacking/os.asm, MIT licensed.
; BDOS version/type queries and DOS Plus console restoration for VI.
; No external library dependencies.
codeseg segment para public 'code'
dataseg segment para public 'data'
dataseg ends
    assume cs:codeseg, ds:dataseg

	        public	ostype_
ostype_ 	proc	near
            push	bp
            mov 	bp,sp
            push    ds
            push	es
            push	di
            push	si
            push    bx
            push    cx
            mov     cx,0Ch
            int     0E0h
            mov     al,ah
            xor     ah,ah
            cmp     al,0
            jnz     ostypeend
            mov     al,10h
ostypeend:
            pop     cx
            pop     bx
            pop	    si
            pop 	di
            pop     es
            pop     ds
            pop     bp
            ret
ostype_     endp

	        public	osver_
osver_  	proc	near
            push	bp
            mov 	bp,sp
            push    ds
            push	es
            push	di
            push	si
            push    bx
            push    cx
            mov     cx,0Ch
            int     0E0h
            xor     ah,ah
            pop     cx
            pop     bx
            pop	    si
            pop 	di
            pop     es
            pop     ds
            pop     bp
            ret
osver_      endp

; DOS Plus retains a hardware scrolling origin independently of BIOS cursor
; coordinates. Re-enter the current text mode through its installed INT 10h
; hook so both XIOS and the ROM reset their state. This intentionally clears
; the screen and homes the cursor. Leave graphics modes alone.
; Called only after C has identified non-Concurrent BDOS 41h.
            public dosplus_crtreset_
dosplus_crtreset_ proc near
            pushf
            push bp
            push ds
            push es
            push si
            push di
            push bx
            push cx
            push dx
            mov ah,0Fh
            int 10h
            and al,7Fh
            cmp al,3
            jbe dp_crtreset_text
            cmp al,7
            jne dp_crtreset_done
dp_crtreset_text:
            xor ah,ah
            int 10h
dp_crtreset_done:
            pop dx
            pop cx
            pop bx
            pop di
            pop si
            pop es
            pop ds
            pop bp
            xor ax,ax
            popf
            ret
dosplus_crtreset_ endp

codeseg ends
    end
