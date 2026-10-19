; Local subset of cpm86-hacking/os.asm, MIT licensed.
; Only BDOS function 12 version/type queries are needed by VI.
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

codeseg ends
    end
