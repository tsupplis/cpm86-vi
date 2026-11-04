codeseg segment para public 'code'
dataseg segment para public 'data'
dataseg ends
    assume cs:codeseg, ds:dataseg

    public vi_yseg_init_
vi_yseg_init_ proc near
    ; Base-page EXTRA descriptor: 24-bit last offset/length, then segment.
    cmp byte ptr ds:[0Eh],0
    jne yc_present
    cmp word ptr ds:[0Ch],0FFFFh
    jb yc_missing
yc_present:
    mov ax,word ptr ds:[0Fh]
    ret
yc_missing:
    xor ax,ax
    ret
vi_yseg_init_ endp

    public vi_yseg_capacity_
vi_yseg_capacity_ proc near
    mov ax,38016
    ret
vi_yseg_capacity_ endp

    public vi_yseg_free_
vi_yseg_free_ proc near
    ; The loader owns this group until the process exits.
    mov ax,1
    ret
vi_yseg_free_ endp
codeseg ends
    end
