package com.piaqee.salescopilot

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity: ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme=lightColorScheme(primary=androidx.compose.ui.graphics.Color(0xFF6750A4))) { SalesApp() } }
    }
}

private val sections = listOf("工作台","客户","AI助手","跟进","我的")
@Composable fun SalesApp() {
    var selected by remember { mutableIntStateOf(0) }
    var medical by remember { mutableStateOf(false) }
    Scaffold(
        topBar={ Column(Modifier.padding(16.dp)) {
            Text("美容医美 AI 销售副驾",style=MaterialTheme.typography.titleLarge)
            Spacer(Modifier.height(8.dp))
            Row { FilterChip(selected=!medical,onClick={medical=false},label={Text("生活美容")});Spacer(Modifier.width(8.dp));FilterChip(selected=medical,onClick={medical=true},label={Text("医疗美容")}) }
        } },
        bottomBar={ NavigationBar { sections.forEachIndexed { i,s -> NavigationBarItem(selected=selected==i,onClick={selected=i},icon={ Text(listOf("⌂","◉","✦","✓","⚙")[i]) },label={Text(s)}) } } }
    ) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding).padding(horizontal=16.dp), verticalArrangement=Arrangement.spacedBy(12.dp)) {
            item { Text(sections[selected], style=MaterialTheme.typography.headlineSmall) }
            val cards=when(selected) {
                0 -> listOf("今日待办 · 连接后端后展示","重点客户 · AI画像与分级","智能拓客 · 推荐关系追踪")
                1 -> listOf("客户档案 · 待接入客户API","客户记忆 · 待接入","客户等级 · 待接入")
                2 -> listOf("AI实时助手 · 尚未接入语音服务","需要客户授权录音与转写","医学判断必须交由专业人员")
                3 -> listOf("预约管理 · 待接入","客户跟进任务 · 待接入")
                else -> listOf("双账户钱包 · 后端沙盒已提供","充值余额和积分分别核算","1积分抵扣1元，单笔最多抵扣50%",if(medical) "医美奖励与抵扣默认关闭" else "直接推荐5%为沙盒默认参数")
            }
            items(cards) { entry -> ElevatedCard(Modifier.fillMaxWidth()) { Text(entry,Modifier.padding(20.dp)) } }
            item { Text("开发预览版：界面为本地示例，未接入真实客户或收付款服务。",style=MaterialTheme.typography.bodySmall) }
        }
    }
}
