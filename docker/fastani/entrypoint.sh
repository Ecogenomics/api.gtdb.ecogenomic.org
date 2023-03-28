nice -n 19 rq worker --url "redis://:${REDIS_PASS}@${REDIS_HOST}" "${FASTANI_Q_PRIORITY}" "${FASTANI_Q_NORMAL}" "${FASTANI_Q_LOW}"
