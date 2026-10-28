#!/bin/bash
# Instala o zipmenu como wrapper global do emulatorlauncher (sem es_systems_*.cfg).
# Pode rodar quantas vezes quiser e ate em paralelo (o custom.sh chama varias vezes no boot):
#   - usa trava (so uma instancia por vez)
#   - se ja estiver instalado corretamente, nao mexe em nada
#   - senao desmonta tudo e reinstala, conferindo o resultado (se falhar, desfaz e usa o original)
# Log de cada execucao: /userdata/system/zipmenu-boot.log. Desfazer: ver zipmenu-off.
WRAP=/userdata/system/zipmenu-launch.sh
RUN=/tmp/zipmenu-wrap.sh
TARGET=/usr/bin/emulatorlauncher
REAL=/tmp/emulatorlauncher.real
EXCL=/userdata/system/zipmenu-exclude.txt
LOG=/userdata/system/zipmenu-boot.log
LOCK=/var/run/zipmenu-hook.lock

log() { echo "$(date +%H:%M:%S) [$$] $*" >> "$LOG"; }
layers() { grep -c " $1 " /proc/mounts; }
unstack() {
  local n=0
  while [ "$(layers "$1")" -gt 0 ] && [ "$n" -lt 10 ]; do
    umount "$1" 2>/dev/null || umount -l "$1" 2>/dev/null || break
    n=$((n+1))
  done
}

[ -f "$WRAP" ] || { echo "falta $WRAP"; log "ERRO: falta $WRAP"; exit 1; }

# trava: evita duas instancias empilhando mounts ao mesmo tempo
exec 9>"$LOCK"
flock -w 30 9 || { log "lock ocupado, saindo"; exit 0; }

# lista de exclusao padrao (so cria se nao existir)
if [ ! -f "$EXCL" ]; then
  printf '%s\n' mame fbneo neogeo neogeocd naomi naomi2 atomiswave cps1 cps2 cps3 \
    model2 model3 daphne scummvm dos pc98 pico8 tic80 lutro solarus openbor easyrpg \
    wiiu switch windows steam ports psx saturn segacd pcenginecd dreamcast 3do cdi > "$EXCL"
fi

# ja instalado e correto? (1 camada em cada, TARGET = wrapper, REAL = original diferente do wrapper)
if [ "$(layers "$TARGET")" = 1 ] && [ "$(layers "$REAL")" = 1 ] \
   && cmp -s "$TARGET" "$WRAP" && [ -s "$REAL" ] && ! cmp -s "$REAL" "$WRAP"; then
  log "ok (ja instalado)"; echo "zipmenu: ok"; exit 0
fi

# desfaz tudo que estiver empilhado (TARGET primeiro, depois REAL)
unstack "$TARGET"
unstack "$REAL"

# agora TARGET tem que ser o original de fabrica, nunca o wrapper
if cmp -s "$TARGET" "$WRAP"; then
  log "ERRO: $TARGET ainda e o wrapper apos desmontar"; echo "falha: $TARGET ainda e o wrapper"; exit 1
fi

rm -f "$RUN" "$REAL"
cp "$WRAP" "$RUN" && chmod +x "$RUN" || { log "ERRO ao copiar wrapper"; echo "falha ao copiar o wrapper"; exit 1; }
touch "$REAL"
mount --bind "$TARGET" "$REAL" || { log "ERRO ao guardar o original"; echo "falha ao guardar o original"; exit 1; }
mount --bind "$RUN" "$TARGET" || { unstack "$REAL"; log "ERRO ao instalar o wrapper"; echo "falha ao instalar o wrapper"; exit 1; }

# confere o resultado; se algo estiver errado, desfaz tudo (melhor o original do que tela preta)
if [ "$(layers "$TARGET")" = 1 ] && [ "$(layers "$REAL")" = 1 ] \
   && cmp -s "$TARGET" "$WRAP" && [ -s "$REAL" ] && ! cmp -s "$REAL" "$WRAP"; then
  log "instalado"; echo "zipmenu: instalado"
else
  unstack "$TARGET"; unstack "$REAL"
  log "ERRO: verificacao final falhou, desfeito (usando o original)"
  echo "falha na verificacao; zipmenu desfeito"
  exit 1
fi
