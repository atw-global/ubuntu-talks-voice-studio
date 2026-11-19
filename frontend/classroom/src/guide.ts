export type GuidePhase = 'welcome' | 'listening' | 'heard' | 'practice' | 'done' | 'locked'

export const GUIDE: Record<GuidePhase, { title: string; body: string }> = {
  welcome: {
    title: "Welcome — I'm Mrs Ubuntu, and I'll guide you through this lesson.",
    body: 'First, listen for the difference between greeting one person and greeting a group.',
  },
  listening: {
    title: 'Listen with me.',
    body: 'Follow the conversation below. The highlighted line is the one being spoken.',
  },
  heard: {
    title: 'Play the conversation again, then try the response yourself.',
    body: 'Listen carefully to how the greeting changes when speaking to one person and to a group.',
  },
  practice: {
    title: 'Good. Next, try the exercise.',
    body: 'Check your understanding of the greeting. You can play any line again.',
  },
  done: {
    title: "You've completed the opening step.",
    body: "The next stages help you understand, practise, and use the greeting with confidence. When you're ready, continue by enrolling.",
  },
  locked: {
    title: 'This stage continues Lesson 1.',
    body: 'You are in the free opening. The rest of the path opens when your membership for this course is confirmed.',
  },
}
