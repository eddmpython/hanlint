// 시트 fixture. 주석의 한국어는 글이 아니다.
import { Banner } from './kit.js'

const LABELS = { pending: '승인 대기', failed: '요청을 완료하지 못했습니다' }

export function Sample ({ failure, count }) {
  console.log('개발자만 보는 줄입니다')
  if (failure) throw new Error('내부 오류입니다')
  return <section>
    <h1>승인된 대시보드를 확인하고 있습니다.</h1>
    <p>접수 실패 · 코드: {failure}</p>
    <span>{count}개 회사</span>
    <Banner title="사전 승인 IP가 필요합니다">{`최대 ${count}개 · 추가 불가`}</Banner>
    <button onClick={() => go('설정')}>다시 시도</button>
  </section>
}
