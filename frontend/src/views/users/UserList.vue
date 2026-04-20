<template>
  <el-card shadow="never">
    <!-- 搜索栏 -->
    <el-form :inline="true" :model="query" @submit.prevent="fetchData">
      <el-form-item label="关键词">
        <el-input v-model="query.keyword" placeholder="用户名/姓名" clearable style="width:160px" />
      </el-form-item>
      <el-form-item label="角色">
        <el-select v-model="query.role" placeholder="全部角色" clearable style="width:120px">
          <el-option label="管理员" value="admin" />
          <el-option label="教师" value="teacher" />
          <el-option label="辅导员" value="counselor" />
          <el-option label="学生" value="student" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchData">查询</el-button>
        <el-button type="success" :icon="Plus" @click="openDialog()">新增用户</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="users" v-loading="loading" stripe>
      <el-table-column prop="username" label="用户名" width="130" />
      <el-table-column prop="real_name" label="姓名" width="100" />
      <el-table-column label="角色" width="90">
        <template #default="{ row }">
          <el-tag :type="roleTagType[row.role]" size="small">{{ ROLE_MAP[row.role] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ row.created_at?.slice(0, 19).replace('T', ' ') }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link :type="row.is_active ? 'warning' : 'success'"
            @click="handleToggle(row)">{{ row.is_active ? '禁用' : '启用' }}</el-button>
          <el-popconfirm title="确认删除该用户？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" v-model:page-size="perPage"
      :total="total" layout="total, sizes, prev, pager, next"
      :page-sizes="[10, 20, 50]" style="margin-top:16px;justify-content:flex-end"
      @change="fetchData" />

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editTarget ? '编辑用户' : '新增用户'" width="460px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!editTarget" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="form.real_name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" style="width:100%">
            <el-option label="管理员" value="admin" />
            <el-option label="教师" value="teacher" />
            <el-option label="辅导员" value="counselor" />
            <el-option label="学生" value="student" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="密码" :prop="editTarget ? '' : 'password'">
          <el-input v-model="form.password" type="password" show-password
            :placeholder="editTarget ? '不填则不修改' : '至少6位'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { usersApi } from '@/api/users'

const ROLE_MAP = { admin: '管理员', teacher: '教师', counselor: '辅导员', student: '学生' }
const roleTagType = { admin: 'danger', teacher: 'primary', counselor: 'warning', student: '' }

const users = ref([]), loading = ref(false), saving = ref(false)
const page = ref(1), perPage = ref(20), total = ref(0)
const query = reactive({ keyword: '', role: '' })
const dialogVisible = ref(false), editTarget = ref(null)
const formRef = ref()
const form = reactive({ username: '', real_name: '', role: 'teacher', email: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [{ required: true, min: 6, message: '密码至少6位', trigger: 'blur' }],
}

async function fetchData() {
  loading.value = true
  try {
    const res = await usersApi.list({ page: page.value, per_page: perPage.value, ...query })
    users.value = res.data.items
    total.value = res.data.pagination.total
  } finally { loading.value = false }
}

function openDialog(row = null) {
  editTarget.value = row
  Object.assign(form, { username: '', real_name: '', role: 'teacher', email: '', password: '' })
  if (row) Object.assign(form, { username: row.username, real_name: row.real_name, role: row.role, email: row.email || '' })
  dialogVisible.value = true
}

async function handleSave() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = { ...form }
    if (editTarget.value && !payload.password) delete payload.password
    if (editTarget.value) {
      await usersApi.update(editTarget.value.id, payload)
    } else {
      await usersApi.create(payload)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    fetchData()
  } finally { saving.value = false }
}

async function handleToggle(row) {
  await usersApi.toggleActive(row.id, !row.is_active)
  ElMessage.success(row.is_active ? '已禁用' : '已启用')
  fetchData()
}

async function handleDelete(id) {
  await usersApi.remove(id)
  ElMessage.success('删除成功')
  fetchData()
}

onMounted(fetchData)
</script>
