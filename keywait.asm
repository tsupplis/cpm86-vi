; Private keyboard wait primitive. Caller gates this to classic CP/M-86.
; Preserve registers and flags. Keyboard/timer interrupts resume execution.
; A key arriving between poll and HLT can wait until the next timer tick.
codeseg segment para public 'code'
    public vi_key_idle_
vi_key_idle_ proc near
    pushf
    sti
    hlt
    popf
    ret
vi_key_idle_ endp
codeseg ends
    end
