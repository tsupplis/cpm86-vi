codeseg segment para public 'code'
    extrn exitcs:word
dataseg segment para public 'data'
dataseg ends
    assume cs:codeseg, ds:dataseg

    public vi_yseg_init_
vi_yseg_init_ proc near
    push bx
    push dx
    push es
    ; Aztec saved the incoming PSP segment in its code-segment exitcs.
    mov ax,cs:exitcs
    mov es,ax
    mov dx,word ptr es:[2]
    mov ax,ds
    add ax,1000h
    jc yd1_missing
    mov bx,ax
ifdef VI_DOS1_COM
    add bx,800h
else
    add bx,1000h
endif
    jc yd1_missing
    cmp bx,dx
    ja yd1_missing
    jmp short yd1_done
yd1_missing:
    xor ax,ax
yd1_done:
    pop es
    pop dx
    pop bx
    ret
vi_yseg_init_ endp

    public vi_yseg_capacity_
vi_yseg_capacity_ proc near
ifdef VI_DOS1_COM
    mov ax,18432
else
    mov ax,38016
endif
    ret
vi_yseg_capacity_ endp

    public vi_yseg_free_
vi_yseg_free_ proc near
    ; DOS 1 owns the whole process block; the near heap ends below this area.
    mov ax,1
    ret
vi_yseg_free_ endp
codeseg ends
    end
