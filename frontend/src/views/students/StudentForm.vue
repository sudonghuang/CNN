<template>
  <el-card shadow="never" :header="isEdit ? '编辑学生' : '新增学生'" style="max-width:600px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="学号" prop="student_id">
        <el-input v-model="form.student_id" :disabled="isEdit" placeholder="如：2022214380" />
      </el-form-item>
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" placeholder="真实姓名" />
      </el-form-item>
      <el-form-item label="班级" prop="class_name">
        <el-input v-model="form.class_name" placeholder="如：计算机22-1班" />
      </el-form-item>
      <el-form-item label="院系">
        <el-input v-model="form.department" placeholder="如：计算机科学与技术学院" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="handleSubmit">保存</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { studentsApi } from '@/api/students'

const route = useRoute(), router = useRouter()
const isEdit = computed(() => !!route.params.id)
const loading = ref(false)
const formRef = ref()
const form = reactive({ student_id: '', name: '', class_name: '', department: '' })
const rules = {
  student_id: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  class_name: [{ required: true, message: '请输入班级', trigger: 'blur' }],
}

onMounted(async () => {
  if (isEdit.value) {
    const res = await studentsApi.get(route.params.id)
    Object.assign(form, res.data)
  }
})

async function handleSubmit() {
  await formRef.value.validate()
  loading.value = true
  try {
    if (isEdit.value) {
      await studentsApi.update(route.params.id, form)
    } else {
      await studentsApi.create(form)
    }
    ElMessage.success('保存成功')
    router.push('/students')
  } finally { loading.value = false }
}
</script>
